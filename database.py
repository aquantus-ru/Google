import sqlite3
import threading
import queue
import time
import os

class Database:
    def __init__(self, db_file="search_engine.db"):
        self.db_file = db_file
        self.write_queue = queue.Queue()
        self.running = True

        # Initialize the database
        self._init_db()

        # Start the writer thread
        self.writer_thread = threading.Thread(target=self._write_worker, daemon=True)
        self.writer_thread.start()

    def _init_db(self):
        """Initializes the database with FTS5 table."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        # Create FTS5 table for full-text search
        # Using FTS5 requires the fts5 extension to be enabled in SQLite.
        # Python's sqlite3 usually comes with it.
        try:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
                    url,
                    title,
                    content
                )
            ''')
        except sqlite3.OperationalError as e:
            # Fallback or error handling if FTS5 is not available?
            # For now assume it is available as per requirements.
            print(f"Error creating FTS5 table: {e}")
            raise e

        # Standard table for visited URLs to avoid re-crawling could be useful,
        # but FTS5 table can also be queried for existence.
        # However, for efficiency, maybe a separate table for visited URLs?
        # Let's keep it simple and use the FTS table or a separate set in memory for now.
        # Requirement says "Store page titles, content, and URLs in SQLite using FTS5".

        conn.commit()
        conn.close()

    def _write_worker(self):
        """Worker thread that handles all database writes."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        while self.running or not self.write_queue.empty():
            try:
                # Get a task from the queue
                # timeout allows checking self.running periodically
                task = self.write_queue.get(timeout=1)

                query, params = task
                try:
                    c.execute(query, params)
                    conn.commit()
                except Exception as e:
                    print(f"Database write error: {e}")
                finally:
                    self.write_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker thread error: {e}")

        conn.close()

    def insert_page(self, url, title, content):
        """Queues a page insertion."""
        query = "INSERT INTO pages(url, title, content) VALUES (?, ?, ?)"
        self.write_queue.put((query, (url, title, content)))

    def search(self, keyword):
        """Searches the database. Runs in the calling thread (read operation)."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        # FTS5 search query
        # Using MATCH operator
        try:
            # simple ranking by bm25 is default in FTS5
            c.execute("SELECT url, title, snippet(pages, 2, '<b>', '</b>', '...', 64) FROM pages WHERE pages MATCH ? ORDER BY rank", (keyword,))
            results = c.fetchall()
        except Exception as e:
            print(f"Search error: {e}")
            results = []
        finally:
            conn.close()

        return results

    def get_indexed_count(self):
        """Returns the number of indexed pages."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        try:
            c.execute("SELECT count(*) FROM pages")
            count = c.fetchone()[0]
        except:
            count = 0
        finally:
            conn.close()
        return count


    def get_all_pages(self, limit=100, offset=0):
        """Retrieves a list of pages for the explore view."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        try:
            # fts5 has an implicit rowid
            c.execute("SELECT rowid, url, title FROM pages LIMIT ? OFFSET ?", (limit, offset))
            results = c.fetchall()
        except Exception as e:
            print(f"Error getting pages: {e}")
            results = []
        finally:
            conn.close()
        return results

    def get_page(self, rowid):
        """Retrieves a specific page's full details."""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        try:
            c.execute("SELECT rowid, url, title, content FROM pages WHERE rowid=?", (rowid,))
            result = c.fetchone()
        except Exception as e:
            print(f"Error getting page: {e}")
            result = None
        finally:
            conn.close()
        return result

    def update_page(self, rowid, url, title, content):
        """Queues a page update."""
        query = "UPDATE pages SET url=?, title=?, content=? WHERE rowid=?"
        self.write_queue.put((query, (url, title, content, rowid)))

    def delete_page(self, rowid):
        """Queues a page deletion."""
        query = "DELETE FROM pages WHERE rowid=?"
        self.write_queue.put((query, (rowid,)))

    def close(self):
        """Stops the writer thread and closes connection."""
        self.running = False
        self.writer_thread.join()
