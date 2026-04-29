from flask import Flask, render_template, request, jsonify, redirect, url_for
import threading

class WebInterface:
    def __init__(self, db, crawler):
        self.app = Flask(__name__)
        self.db = db
        self.crawler = crawler
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            stats = {
                'indexed_pages': self.db.get_indexed_count(),
                'queue_size': self.crawler.get_queue_size()
            }
            return render_template('index.html', stats=stats)

        @self.app.route('/search')
        def search():
            query = request.args.get('q', '')
            results = []
            if query:
                results = self.db.search(query)
            return render_template('results.html', query=query, results=results)


        @self.app.route('/explore')
        def explore():
            pages = self.db.get_all_pages()
            return render_template('explore.html', pages=pages)

        @self.app.route('/explore/add', methods=['GET', 'POST'])
        def add_page():
            if request.method == 'POST':
                url = request.form.get('url')
                title = request.form.get('title')
                content = request.form.get('content')
                if url and title and content:
                    self.db.insert_page(url, title, content)
                return redirect(url_for('explore'))
            return render_template('page_form.html', action="Add")

        @self.app.route('/explore/edit/<int:rowid>', methods=['GET', 'POST'])
        def edit_page(rowid):
            if request.method == 'POST':
                url = request.form.get('url')
                title = request.form.get('title')
                content = request.form.get('content')
                if url and title and content:
                    self.db.update_page(rowid, url, title, content)
                return redirect(url_for('explore'))

            page = self.db.get_page(rowid)
            if not page:
                return redirect(url_for('explore'))

            # Create a dictionary-like object to pass to template
            page_data = {'rowid': page[0], 'url': page[1], 'title': page[2], 'content': page[3]}
            return render_template('page_form.html', action="Edit", page=page_data)

        @self.app.route('/explore/delete/<int:rowid>', methods=['POST'])
        def delete_page(rowid):
            self.db.delete_page(rowid)
            return redirect(url_for('explore'))

        @self.app.route('/status')
        def status():
            return jsonify({
                'indexed_pages': self.db.get_indexed_count(),
                'queue_size': self.crawler.get_queue_size()
            })

    def run(self, host='0.0.0.0', port=5000):
        # Disable reloader to avoid issues in threads
        self.app.run(host=host, port=port, debug=False, use_reloader=False)

def start_web_server(db, crawler):
    web = WebInterface(db, crawler)
    web.run()
