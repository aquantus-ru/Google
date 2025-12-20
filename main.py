import threading
import time
import sys
import signal
from database import Database
from crawler import Crawler
from web import start_web_server

class SearchEngineShell:
    def __init__(self):
        print("Initializing components...")
        self.db = Database()
        self.crawler = Crawler(self.db)
        self.running = True

        # Handle SIGTERM for graceful shutdown on kill
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, sig, frame):
        print("\nSignal received. Shutting down...")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        if self.running:
            self.running = False
            print("Closing database...")
            self.db.close()

    def start_web(self):
        print("Starting Web Interface on http://localhost:5000")
        web_thread = threading.Thread(target=start_web_server, args=(self.db, self.crawler), daemon=True)
        web_thread.start()

    def print_menu(self):
        print("\n--- Search Engine Console ---")
        print("1. Run Crawler (seeds.txt)")
        print("2. Run Deep Crawler (process found links)")
        print("3. Search")
        print("4. Show Status")
        print("5. Exit")
        print("-----------------------------")

    def run_menu(self):
        self.start_web()

        while self.running:
            try:
                self.print_menu()
                choice = input("Select an option: ").strip()

                if choice == '1':
                    print("\nLoading seeds from seeds.txt...")
                    self.crawler.load_seeds()
                    print("Starting crawler...")
                    crawl_thread = threading.Thread(target=self.crawler.run)
                    crawl_thread.start()
                    print("Crawler started in background.")

                elif choice == '2':
                    if self.crawler.get_queue_size() == 0:
                        print("\nQueue is empty. Run Crawler first or ensure links were found.")
                    else:
                        print(f"\nStarting Deep Crawler with {self.crawler.get_queue_size()} links...")
                        crawl_thread = threading.Thread(target=self.crawler.run)
                        crawl_thread.start()
                        print("Deep Crawler started in background.")

                elif choice == '3':
                    query = input("\nEnter search query: ").strip()
                    if query:
                        results = self.db.search(query)
                        print(f"\nFound {len(results)} results:")
                        for i, (url, title, snippet) in enumerate(results, 1):
                            print(f"{i}. {title}")
                            print(f"   URL: {url}")
                            print(f"   Snippet: {snippet}")
                            print("")
                    else:
                        print("Empty query.")

                elif choice == '4':
                    print("\n--- Status ---")
                    print(f"Indexed Pages: {self.db.get_indexed_count()}")
                    print(f"Crawler Queue Size: {self.crawler.get_queue_size()}")

                elif choice == '5':
                    print("\nExiting...")
                    self.cleanup()
                    sys.exit(0)

                else:
                    print("Invalid option. Try again.")

            except KeyboardInterrupt:
                print("\nInterrupted. Exiting...")
                self.cleanup()
                sys.exit(0)
            except EOFError:
                print("\nExiting...")
                self.cleanup()
                sys.exit(0)
            except Exception as e:
                print(f"Error: {e}")

def main():
    app = SearchEngineShell()
    app.run_menu()

if __name__ == "__main__":
    main()
