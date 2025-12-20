import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import concurrent.futures
import threading
from database import Database
import os

class Crawler:
    def __init__(self, db: Database, max_workers=5):
        self.db = db
        self.max_workers = max_workers
        self.visited_urls = set()
        self.lock = threading.Lock()
        self.queue = []
        self.discovered_file = "discovered.txt"

        # Ensure discovered.txt exists
        if not os.path.exists(self.discovered_file):
            open(self.discovered_file, 'w').close()

    def load_seeds(self, seeds_file="seeds.txt"):
        """Loads URLs from seeds.txt into the queue."""
        if os.path.exists(seeds_file):
            with open(seeds_file, 'r') as f:
                with self.lock:
                    for line in f:
                        url = line.strip()
                        if url and url not in self.visited_urls and url not in self.queue:
                            self.queue.append(url)
        else:
            print(f"Seeds file {seeds_file} not found.")

    def run(self):
        """Processes the current queue using ThreadPoolExecutor."""
        with self.lock:
            urls_to_crawl = list(self.queue)
            self.queue = []

        if not urls_to_crawl:
            print("Queue is empty.")
            return

        print(f"Starting crawl with {len(urls_to_crawl)} URLs...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.crawl_page, url): url for url in urls_to_crawl}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    links = future.result()
                    # Add discovered links to queue for Deep Crawler
                    with self.lock:
                        for link in links:
                            if link not in self.visited_urls and link not in self.queue:
                                self.queue.append(link)
                except Exception as e:
                    print(f"Error crawling {url}: {e}")

    def crawl_page(self, url):
        """Fetches a page, parses it, stores in DB, and extracts links."""
        with self.lock:
            if url in self.visited_urls:
                return []
            self.visited_urls.add(url)

        try:
            # Set a timeout and user-agent
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; MySearchEngine/1.0)'}
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                print(f"Failed to fetch {url}: Status {response.status_code}")
                return []

            if 'text/html' not in response.headers.get('Content-Type', ''):
                return []

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = soup.title.string if soup.title else url

            # Extract text from specific tags
            for script in soup(["script", "style"]):
                script.extract()

            # A simple approach: just get all text from body.
            # This covers article, header, footer, etc.
            body_text = soup.get_text(separator=' ', strip=True)

            # Store in DB
            self.db.insert_page(url, title, body_text)

            # Extract links
            links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                parsed_url = urlparse(full_url)

                if parsed_url.scheme in ['http', 'https']:
                    links.append(full_url)

                    # Check for new domain
                    domain = parsed_url.netloc
                    self._check_new_domain(domain)

            return links

        except Exception as e:
            print(f"Exception crawling {url}: {e}")
            return []

    def _check_new_domain(self, domain):
        """Appends new domains to discovered.txt."""
        if not hasattr(self, 'known_domains'):
             # Load existing domains from file
             self.known_domains = set()
             if os.path.exists(self.discovered_file):
                 with open(self.discovered_file, 'r') as f:
                     for line in f:
                         self.known_domains.add(line.strip())

        if domain not in self.known_domains:
            with self.lock:
                if domain not in self.known_domains: # Double check locking
                    self.known_domains.add(domain)
                    with open(self.discovered_file, 'a') as f:
                        f.write(domain + '\n')

    def get_queue_size(self):
        with self.lock:
            return len(self.queue)
