from flask import Flask, render_template, request, jsonify
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
