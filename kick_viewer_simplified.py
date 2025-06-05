import re
import time
import m3u8
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import sys
from typing import Optional, Dict, Any, List, Tuple
import os
from urllib.parse import urlparse, urljoin
import threading
import logging
import atexit
import random
import signal
import psutil
import asyncio
from dataclasses import dataclass
import gzip
import brotli
from io import BytesIO
import requests

try:
    import tls_client
    TLS_CLIENT_AVAILABLE = True
    print("✅ tls-client is used - TLS bypass is active!")
except ImportError:
    TLS_CLIENT_AVAILABLE = False
    print("⚠️  tls-client not found: pip install tls-client")

try:
    import httpx
    HTTPX_AVAILABLE = True
    print("✅ httpx is used - HTTP/2 is active!")
except ImportError:
    HTTPX_AVAILABLE = False
    print("⚠️  httpx not found: pip install httpx[http2]")

try:
    from requests_html import HTMLSession
    REQUESTS_HTML_AVAILABLE = True
    print("✅ requests-html is used - JS rendering is active!")
except ImportError:
    REQUESTS_HTML_AVAILABLE = False
    print("⚠️  requests-html not found: pip install requests-html")

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
    print("✅ using cloudscraper - Cloudflare bypass active!")
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False
    print("⚠️  cloudscraper bulunamadı: pip install cloudscraper")

try:
    import colorama
    from colorama import Fore, Style, Back
    colorama.init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    class Fore:
        RED = '\033[31m'
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        BLUE = '\033[34m'
        MAGENTA = '\033[35m'
        CYAN = '\033[36m'
        WHITE = '\033[37m'
        BLACK = '\033[30m'
        LIGHTRED_EX = '\033[91m'
        LIGHTGREEN_EX = '\033[92m'
        LIGHTYELLOW_EX = '\033[93m'
        LIGHTBLUE_EX = '\033[94m'
        LIGHTMAGENTA_EX = '\033[95m'
        LIGHTCYAN_EX = '\033[96m'
        RESET = '\033[0m'
    
    class Style:
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        RESET_ALL = '\033[0m'
    
    class Back:
        BLACK = '\033[40m'
        RED = '\033[41m'
        GREEN = '\033[42m'
        YELLOW = '\033[43m'
        BLUE = '\033[44m'
        MAGENTA = '\033[45m'
        CYAN = '\033[46m'
        WHITE = '\033[47m'
        RESET = '\033[0m'

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configuration constants - ULTIMATE BYPASS
class Config:
    USER_AGENTS = [
        # Chrome Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        # Chrome Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Mobile
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    ]
    
    # Multiple endpoint support
    KICK_ENDPOINTS = [
        "https://kick.com",
        "https://m.kick.com",  # Mobile endpoint
        "https://www.kick.com",
    ]
    
    # Smart timing
    REQUEST_TIMEOUT = (20, 45)
    RETRY_DELAY_MIN = 2
    RETRY_DELAY_MAX = 8
    BATCH_DELAY = 0.3
    MAINTENANCE_INTERVAL = 4
    MAX_RETRIES = 7  
    MAX_CONSECUTIVE_FAILURES = 6
    SEGMENT_BUFFER_SIZE = 2048
    PLAYBACK_INTERVAL = 3
    STREAM_TIMEOUT = 400
    
    # Smart rate limiting
    PROXY_WARMUP_DELAY = 1
    PROXY_COOLDOWN = 10
    REQUEST_RATE_LIMIT = 0.5  
    
    # Performance settings
    VIEWERS_PER_PROXY = 20
    MAX_CONCURRENT_THREADS = 2000
    BATCH_SIZE = 500
    TARGET_MULTIPLIER = 1.8
    RAPID_START_BATCHES = 4

@dataclass
class ProxyStats:
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0
    last_success: float = 0
    is_warmed_up: bool = False
    response_times: List[float] = None
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []

class Logger:
    """Enhanced logging system with beautiful output"""
    
    @staticmethod
    def header(text: str):
        """Print beautiful header"""
        length = len(text) + 4
        border = "═" * length
        print(f"\n{Fore.LIGHTCYAN_EX}{Style.BRIGHT}╔{border}╗")
        print(f"║  {text}  ║")
        print(f"╚{border}╝{Style.RESET_ALL}")
    
    @staticmethod
    def section(text: str):
        """Print section header"""
        print(f"\n{Fore.LIGHTBLUE_EX}{Style.BRIGHT}▓▓ {text} ▓▓{Style.RESET_ALL}")
    
    @staticmethod
    def success(icon: str, message: str):
        """Print success message"""
        print(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{icon} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def warning(icon: str, message: str):
        """Print warning message"""
        print(f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}{icon} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def error(icon: str, message: str):
        """Print error message"""
        print(f"{Fore.LIGHTRED_EX}{Style.BRIGHT}{icon} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def info(icon: str, message: str):
        """Print info message"""
        print(f"{Fore.LIGHTCYAN_EX}{icon} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def debug(icon: str, message: str):
        """Print debug message"""
        print(f"{Fore.WHITE}{Style.DIM}{icon} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def status(icon: str, message: str, value: str = "", color: str = Fore.LIGHTYELLOW_EX):
        """Print status with value"""
        if value:
            print(f"{color}{Style.BRIGHT}{icon} {message}: {Fore.WHITE}{value}{Style.RESET_ALL}")
        else:
            print(f"{color}{Style.BRIGHT}{icon} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def progress(current: int, total: int, prefix: str = "", suffix: str = ""):
        """Print progress bar"""
        percent = (current / total) * 100 if total > 0 else 0
        filled = int(percent / 4)  # 25 chars max
        bar = "█" * filled + "░" * (25 - filled)
        print(f"\r{Fore.LIGHTCYAN_EX}{prefix} [{bar}] {percent:.1f}% {suffix}{Style.RESET_ALL}", end="", flush=True)
    
    @staticmethod
    def table_header(cols: List[str]):
        """Print table header"""
        separator = "─" * 80
        print(f"\n{Fore.LIGHTBLUE_EX}{separator}{Style.RESET_ALL}")
        header = " | ".join(f"{col:^15}" for col in cols)
        print(f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}{header}{Style.RESET_ALL}")
        print(f"{Fore.LIGHTBLUE_EX}{separator}{Style.RESET_ALL}")
    
    @staticmethod
    def table_row(values: List[str], colors: List[str] = None):
        """Print table row"""
        if not colors:
            colors = [Fore.WHITE] * len(values)
        row = ""
        for i, (value, color) in enumerate(zip(values, colors)):
            row += f"{color}{value:^15}{Style.RESET_ALL}"
            if i < len(values) - 1:
                row += f"{Fore.LIGHTBLUE_EX} | {Style.RESET_ALL}"
        print(row)

class ViewerCounter:
    def __init__(self):
        self._count = 0
        self._target = 0
        self._successful_creates = 0
        self._failed_creates = 0
        self._cloudflare_challenges = 0
        self._tls_bypasses = 0
        self._mobile_requests = 0
        self._js_renders = 0
        self._lock = threading.Lock()
        self._start_time = time.time()
    
    def set_target(self, target: int) -> None:
        with self._lock:
            self._target = max(0, target)
    
    def increment(self) -> bool:
        with self._lock:
            if self._count >= self._target * 1.5:
                return False
            self._count += 1
            return True
    
    def decrement(self) -> None:
        with self._lock:
            self._count = max(0, self._count - 1)
    
    def increment_successful_creates(self) -> None:
        with self._lock:
            self._successful_creates += 1
    
    def increment_failed_creates(self) -> None:
        with self._lock:
            self._failed_creates += 1
    
    def increment_cloudflare_challenges(self) -> None:
        with self._lock:
            self._cloudflare_challenges += 1
    
    def increment_tls_bypasses(self) -> None:
        with self._lock:
            self._tls_bypasses += 1
    
    def increment_mobile_requests(self) -> None:
        with self._lock:
            self._mobile_requests += 1
    
    def increment_js_renders(self) -> None:
        with self._lock:
            self._js_renders += 1
    
    @property
    def count(self) -> int:
        with self._lock:
            return self._count
    
    @property
    def target(self) -> int:
        with self._lock:
            return self._target
    
    @property
    def successful_creates(self) -> int:
        with self._lock:
            return self._successful_creates
    
    @property
    def failed_creates(self) -> int:
        with self._lock:
            return self._failed_creates
    
    @property
    def cloudflare_challenges(self) -> int:
        with self._lock:
            return self._cloudflare_challenges
    
    @property
    def tls_bypasses(self) -> int:
        with self._lock:
            return self._tls_bypasses
    
    @property
    def mobile_requests(self) -> int:
        with self._lock:
            return self._mobile_requests
    
    @property
    def js_renders(self) -> int:
        with self._lock:
            return self._js_renders
    
    @property
    def uptime(self) -> int:
        return int(time.time() - self._start_time)

viewer_counter = ViewerCounter()

class SmartProxyManager:
    def __init__(self, proxy_file: str):
        self.proxies: List[str] = []
        self.proxy_stats: Dict[str, ProxyStats] = {}
        self.current_index = 0
        self.lock = threading.Lock()
        self.failed_proxies: set = set()
        self.warmup_queue: List[str] = []
        self.last_rotation = time.time()
        self.rotation_interval = 240  # 4 minute
        
        self._load_proxies(proxy_file)
        if self.proxies:
            random.shuffle(self.proxies)
            self._initialize_stats()
            Logger.success("✅", f"{len(self.proxies)} smart proxy loaded successfully")
        else:
            Logger.error("❌", "No valid proxies could be loaded!")
    
    def _load_proxies(self, proxy_file: str) -> None:
        try:
            Logger.info("📂", f"Loading proxies from: {proxy_file}")
            with open(proxy_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    proxy = self._format_proxy(line)
                    if proxy:
                        self.proxies.append(proxy)
                        
            Logger.success("📋", f"Loaded {len(self.proxies)} proxies from file")
                        
        except FileNotFoundError:
            Logger.error("❌", f"Proxy file not found: {proxy_file}")
        except Exception as e:
            Logger.error("❌", f"Error loading proxies: {e}")
    
    def _format_proxy(self, proxy_line: str) -> Optional[str]:
        parts = proxy_line.split(':')
        
        if len(parts) == 4:  # ip:port:username:password
            ip, port, username, password = parts
            formatted = f"http://{username}:{password}@{ip}:{port}"
            Logger.debug("🔧", f"Formatted proxy with auth: {ip}:{port}")
            return formatted
        elif len(parts) == 2:  # ip:port
            ip, port = parts
            formatted = f"http://{ip}:{port}"
            Logger.debug("🔧", f"Formatted proxy: {ip}:{port}")
            return formatted
        else:
            Logger.warning("⚠️", f"Invalid proxy format: {proxy_line}")
            return None
    
    def _initialize_stats(self) -> None:
        for proxy in self.proxies:
            self.proxy_stats[proxy] = ProxyStats()
        Logger.info("📊", "Proxy statistics initialized")
    
    def mark_proxy_result(self, proxy: str, success: bool, response_time: float = 0) -> None:
        with self.lock:
            if proxy not in self.proxy_stats:
                return
            
            stats = self.proxy_stats[proxy]
            current_time = time.time()
            
            if success:
                stats.success_count += 1
                stats.last_success = current_time
                stats.response_times.append(response_time)
                if len(stats.response_times) > 10:
                    stats.response_times = stats.response_times[-10:]
                    
                self.failed_proxies.discard(proxy)
            else:
                stats.failure_count += 1
                
                total_attempts = stats.success_count + stats.failure_count
                if total_attempts >= 5 and stats.failure_count / total_attempts > 0.7:
                    self.failed_proxies.add(proxy)
    
    def get_best_proxy(self) -> Optional[str]:
        with self.lock:
            if not self.proxies:
                return None
            
            current_time = time.time()
            
            if current_time - self.last_rotation > self.rotation_interval:
                self._rotate_proxies()
            
            available_proxies = []
            for proxy in self.proxies:
                if proxy in self.failed_proxies:
                    continue
                    
                stats = self.proxy_stats[proxy]
                
                if current_time - stats.last_used < Config.REQUEST_RATE_LIMIT:
                    continue
                    
                available_proxies.append((proxy, stats))
            
            if not available_proxies:
                self.failed_proxies.clear()
                return self.proxies[0] if self.proxies else None
            
            # success rate + response time
            best_proxy = None
            best_score = -1
            
            for proxy, stats in available_proxies:
                total_attempts = stats.success_count + stats.failure_count
                if total_attempts == 0:
                    score = 0.5 
                else:
                    success_rate = stats.success_count / total_attempts
                    avg_response_time = sum(stats.response_times) / len(stats.response_times) if stats.response_times else 5.0
                    
                    score = success_rate * 0.8 - (avg_response_time / 20) * 0.2
                
                if score > best_score:
                    best_score = score
                    best_proxy = proxy
            
            if best_proxy:
                self.proxy_stats[best_proxy].last_used = current_time
                return best_proxy
            
            return None
    
    def _rotate_proxies(self) -> None:
        current_time = time.time()
        
        worst_proxies = []
        for proxy in self.failed_proxies:
            stats = self.proxy_stats[proxy]
            if current_time - stats.last_success > 300:
                worst_proxies.append(proxy)
        
        for proxy in worst_proxies:
            self.failed_proxies.discard(proxy)
            self.proxy_stats[proxy] = ProxyStats()
        
        self.last_rotation = current_time
        random.shuffle(self.proxies)
        
        if worst_proxies:
            Logger.info("🔄", f"Cleaned {len(worst_proxies)} failed proxies and rotated pool")
    
    @property
    def total_proxies(self) -> int:
        return len(self.proxies)
    
    @property
    def failed_proxy_count(self) -> int:
        return len(self.failed_proxies)
    
    @property
    def avg_success_rate(self) -> float:
        with self.lock:
            if not self.proxy_stats:
                return 0.0
            
            total_success = sum(stats.success_count for stats in self.proxy_stats.values())
            total_attempts = sum(stats.success_count + stats.failure_count for stats in self.proxy_stats.values())
            
            return (total_success / total_attempts * 100) if total_attempts > 0 else 0.0

class UltimateBypassSession:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.sessions = {}
        self.current_method = 0
        self.methods = ['tls_client', 'httpx', 'cloudscraper', 'requests_html', 'requests']
        
        # Rate limiting
        self.last_request_time = 0
        
        self._initialize_sessions()
    
    def _initialize_sessions(self):
        """Tüm mevcut session tiplerini initialize et"""
        
        # 1. TLS Client - Timeout fix
        if TLS_CLIENT_AVAILABLE:
            try:
                session = tls_client.Session(
                    client_identifier="chrome_120",
                    random_tls_extension_order=True
                )
                if self.proxy:
                    session.proxies = {"http": self.proxy, "https": self.proxy}
                self.sessions['tls_client'] = session
                Logger.debug("🔐", "TLS-Client session initialized")
            except Exception as e:
                Logger.warning("⚠️", f"TLS-Client init failed: {e}")
        
        # 2. HTTPX (HTTP/2 support)
        if HTTPX_AVAILABLE:
            try:
                session = httpx.Client(
                    http2=True,
                    proxies=self.proxy,
                    timeout=httpx.Timeout(Config.REQUEST_TIMEOUT[1]),
                    headers={
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'User-Agent': random.choice(Config.USER_AGENTS)
                    }
                )
                self.sessions['httpx'] = session
                Logger.debug("🌐", "HTTPX/HTTP2 session initialized")
            except Exception as e:
                Logger.warning("⚠️", f"HTTPX init failed: {e}")
        
        # 3. Cloudscraper (Cloudflare bypass)
        if CLOUDSCRAPER_AVAILABLE:
            try:
                session = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False
                    },
                    delay=1,
                    debug=False
                )
                if self.proxy:
                    session.proxies = {"http": self.proxy, "https": self.proxy}
                self.sessions['cloudscraper'] = session
                Logger.debug("⚡", "CloudScraper session initialized")
            except Exception as e:
                Logger.warning("⚠️", f"CloudScraper init failed: {e}")
        
        # 4. Requests-HTML (JS rendering)
        if REQUESTS_HTML_AVAILABLE:
            try:
                session = HTMLSession()
                if self.proxy:
                    session.proxies = {"http": self.proxy, "https": self.proxy}
                session.headers.update({
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                })
                self.sessions['requests_html'] = session
                Logger.debug("🎭", "Requests-HTML session initialized")
            except Exception as e:
                Logger.warning("⚠️", f"Requests-HTML init failed: {e}")
        
        # 5. Standard Requests (Fallback) 
        try:
            session = requests.Session()
            if self.proxy:
                session.proxies = {"http": self.proxy, "https": self.proxy}
            
            # Force proper headers for decompression
            session.headers.update({
                'Accept-Encoding': 'gzip, deflate, br, identity',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            })
            
            # Mount adapter with retry logic
            adapter = requests.adapters.HTTPAdapter(
                max_retries=requests.adapters.Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[500, 502, 503, 504]
                )
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            
            self.sessions['requests'] = session
            Logger.debug("📡", "Standard Requests session initialized")
        except Exception as e:
            Logger.warning("⚠️", f"Requests init failed: {e}")
    
    def _setup_headers(self, session, method: str):
        """Method'a özel header setup"""
        user_agent = random.choice(Config.USER_AGENTS)
        
        base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": f"en-US,en;q=0.9,tr;q={random.uniform(0.7, 0.8):.1f}",
            "Cache-Control": random.choice(["max-age=0", "no-cache", "no-store"]),
            "Connection": "keep-alive",
            "DNT": str(random.randint(0, 1)),
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": user_agent,
        }
        
        if method in ['tls_client', 'httpx'] and "Chrome" in user_agent:
            base_headers.update({
                "sec-ch-ua": f'"Google Chrome";v="{random.randint(119, 121)}", "Chromium";v="{random.randint(119, 121)}", "Not?A_Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            })
        
        try:
            if hasattr(session, 'headers'):
                session.headers.update(base_headers)
            return base_headers
        except Exception:
            return base_headers
    
    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Smart multi-method GET request with advanced decompression"""
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < Config.REQUEST_RATE_LIMIT:
            time.sleep(Config.REQUEST_RATE_LIMIT - time_since_last)
        
        self.last_request_time = time.time()
        
        available_methods = [method for method in self.methods if method in self.sessions]
        
        if not available_methods:
            return None
        
        start_method = self.current_method % len(available_methods)
        
        for i in range(len(available_methods)):
            method_index = (start_method + i) % len(available_methods)
            method = available_methods[method_index]
            session = self.sessions[method]
            
            try:
                # Header setup
                headers = self._setup_headers(session, method)
                kwargs_copy = kwargs.copy()
                
                if method == 'tls_client':
                    viewer_counter.increment_tls_bypasses()
                    Logger.debug("🔐", "Attempting TLS-Client bypass")
                    # TLS client için special handling - timeout fix
                    kwargs_clean = {k: v for k, v in kwargs_copy.items() if k != 'timeout'}
                    response = session.get(url, **kwargs_clean)
                    
                    mock_response = requests.Response()
                    mock_response.status_code = response.status_code
                    mock_response._content = response.content if hasattr(response, 'content') else response.text.encode()
                    if hasattr(response, 'headers'):
                        mock_response.headers.update(response.headers)
                    mock_response.encoding = 'utf-8'
                    response = mock_response
                    
                elif method == 'httpx':
                    Logger.debug("🌐", "Attempting HTTPX/HTTP2 bypass")
                    response = session.get(url, **kwargs_copy)

                    mock_response = requests.Response()
                    mock_response.status_code = response.status_code
                    mock_response._content = response.content
                    mock_response.headers.update(response.headers)
                    mock_response.encoding = response.encoding or 'utf-8'
                    response = mock_response
                    
                elif method == 'cloudscraper':
                    viewer_counter.increment_cloudflare_challenges()
                    Logger.debug("⚡", "Attempting CloudFlare bypass")
                    response = session.get(url, **kwargs_copy)
                    
                elif method == 'requests_html':
                    viewer_counter.increment_js_renders()
                    Logger.debug("🎭", "Attempting JavaScript rendering")
                    r = session.get(url, **kwargs_copy)
                    # JS render
                    try:
                        r.html.render(timeout=10, wait=2)
                    except Exception:
                        pass
                    response = r
                    
                else:  # requests
                    Logger.debug("📡", "Using standard Requests")
                    response = session.get(url, **kwargs_copy)
                
                # Advanced content decompression
                if response and hasattr(response, 'content'):
                    response = self._fix_content_encoding(response)
                
                self.current_method = method_index
                Logger.debug("✅", f"Method {method} succeeded")
                return response
                
            except Exception as e:
                Logger.debug("❌", f"Method {method} failed: {str(e)[:50]}...")
                continue
        
        return None
    
    def _fix_content_encoding(self, response):
        """Advanced content encoding fix"""
        try:
            # Get content encoding from headers
            content_encoding = response.headers.get('Content-Encoding', '').lower()
            
            Logger.debug("🔧", f"Content-Encoding: {content_encoding or 'none'}")
            Logger.debug("🔧", f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            
            raw_content = response.content
            
            # Manual decompression if needed
            if content_encoding:
                if 'gzip' in content_encoding:
                    try:
                        raw_content = gzip.decompress(raw_content)
                        Logger.debug("✅", "GZIP decompressed successfully")
                    except Exception:
                        Logger.debug("⚠️", "GZIP decompression failed")
                
                elif 'br' in content_encoding or 'brotli' in content_encoding:
                    try:
                        raw_content = brotli.decompress(raw_content)
                        Logger.debug("✅", "Brotli decompressed successfully")
                    except Exception:
                        Logger.debug("⚠️", "Brotli decompression failed")
                
                elif 'deflate' in content_encoding:
                    try:
                        import zlib
                        raw_content = zlib.decompress(raw_content)
                        Logger.debug("✅", "Deflate decompressed successfully")
                    except Exception:
                        Logger.debug("⚠️", "Deflate decompression failed")
            
            # Update response content
            response._content = raw_content
            
            # Force proper encoding detection
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            # Test if content is readable
            try:
                test_text = response.text[:200]
                # Check for binary garbage
                binary_chars = sum(1 for c in test_text if ord(c) < 32 and c not in '\n\r\t\x00')
                
                if binary_chars > 20:  # Still too many binary characters
                    Logger.debug("⚠️", f"Binary content detected ({binary_chars} binary chars)")
                    
                    # Try different encodings
                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            response.encoding = encoding
                            test_text = response.text[:200]
                            binary_chars = sum(1 for c in test_text if ord(c) < 32 and c not in '\n\r\t')
                            if binary_chars < 10:
                                Logger.debug("✅", f"Fixed with {encoding} encoding")
                                break
                        except:
                            continue
                else:
                    Logger.debug("✅", f"Content is readable ({binary_chars} binary chars)")
                    
            except Exception as e:
                Logger.debug("⚠️", f"Content readability test failed: {e}")
            
            return response
            
        except Exception as e:
            Logger.debug("❌", f"Content encoding fix failed: {e}")
            return response

class MultiEndpointKickPlatform:
    def __init__(self, proxy: Optional[str] = None):
        self.session = UltimateBypassSession(proxy)
        self.proxy = proxy
        self.endpoints = Config.KICK_ENDPOINTS.copy()
        random.shuffle(self.endpoints)
    
    def get_stream_url(self, username: str) -> Optional[str]:
        """Multi-endpoint + API stream URL retrieval"""
        
        api_endpoints = [
            f"https://kick.com/api/v1/channels/{username}",
            f"https://kick.com/api/v2/channels/{username}",
            f"https://kick.com/api/v1/channels/{username}/livestream",
            f"https://kick.com/api/v2/channels/{username}/livestream",
        ]
        
        Logger.section("API ENDPOINT TESTING")
        for api_url in api_endpoints:
            try:
                Logger.info("📡", f"Testing API: {api_url.split('/')[-2]}/{api_url.split('/')[-1]}")
                response = self.session.get(api_url, timeout=Config.REQUEST_TIMEOUT)
                
                if response and response.status_code == 200:
                    try:
                        response_text = response.text.strip()
                        Logger.debug("📄", f"API Response: {len(response_text)} chars")
                        
                        # JSON parse
                        if response_text.startswith('{') or response_text.startswith('['):
                            data = json.loads(response_text)
                            Logger.success("✅", "Valid JSON response received")
                            
                            stream_url = self._extract_from_json(data)
                            if stream_url:
                                Logger.success("🎯", "Stream URL found in API response!")
                                return stream_url
                        else:
                            Logger.warning("⚠️", f"Non-JSON response: {response_text[:50]}...")
                            
                    except json.JSONDecodeError as e:
                        Logger.warning("⚠️", f"JSON parse failed: {str(e)[:50]}...")
                elif response:
                    Logger.warning("❌", f"API returned HTTP {response.status_code}")
                else:
                    Logger.error("❌", "No API response received")
                        
            except Exception as e:
                Logger.debug("⚠️", f"API error: {str(e)[:50]}...")
        
        Logger.section("WEB ENDPOINT TESTING")
        for endpoint in self.endpoints:
            try:
                # Desktop endpoint
                desktop_url = f"{endpoint}/{username}"
                Logger.info("🖥️", f"Testing desktop: {endpoint.replace('https://', '')}")
                stream_url = self._try_get_stream_url(desktop_url, is_mobile=False)
                if stream_url:
                    return stream_url
                
                if "m.kick.com" not in endpoint:
                    mobile_endpoint = endpoint.replace("://", "://m.")
                    mobile_url = f"{mobile_endpoint}/{username}"
                    viewer_counter.increment_mobile_requests()
                    Logger.info("📱", f"Testing mobile: {mobile_endpoint.replace('https://', '')}")
                    stream_url = self._try_get_stream_url(mobile_url, is_mobile=True)
                    if stream_url:
                        return stream_url
                
            except Exception as e:
                Logger.debug("❌", f"Endpoint {endpoint} failed: {str(e)[:50]}...")
                continue
        
        Logger.section("JAVASCRIPT RENDERING")
        if REQUESTS_HTML_AVAILABLE:
            try:
                Logger.info("🎭", "Attempting JavaScript rendering...")
                return self._try_js_rendering(username)
            except Exception as e:
                Logger.error("❌", f"JS rendering failed: {str(e)[:50]}...")
        else:
            Logger.warning("⚠️", "JavaScript rendering not available")
        
        return None
    
    def _extract_from_json(self, data: Dict) -> Optional[str]:
        """JSON'dan stream URL çıkar"""
        def recursive_search(obj, keys_to_find):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(search_key in key.lower() for search_key in keys_to_find):
                        if isinstance(value, str) and value.startswith('http') and 'm3u8' in value:
                            return value
                    if isinstance(value, (dict, list)):
                        result = recursive_search(value, keys_to_find)
                        if result:
                            return result
            elif isinstance(obj, list):
                for item in obj:
                    result = recursive_search(item, keys_to_find)
                    if result:
                        return result
            return None
        
        search_keys = ['playback_url', 'hls_url', 'm3u8_url', 'stream_url', 'video_url', 'source', 'url']
        
        Logger.debug("🔍", "Searching for stream URL in JSON...")
        result = recursive_search(data, search_keys)
        
        if result:
            Logger.success("✅", f"Found in JSON: {result[:60]}...")
        else:
            Logger.debug("⚠️", "No stream URL found in JSON")
            Logger.debug("📋", f"JSON structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        
        return result
    
    def _try_js_rendering(self, username: str) -> Optional[str]:
        """JavaScript rendering ile stream URL alma"""
        try:
            Logger.info("🎭", "Starting JavaScript rendering...")
            viewer_counter.increment_js_renders()
            
            if not REQUESTS_HTML_AVAILABLE:
                return None
            
            session = HTMLSession()
            if self.proxy:
                session.proxies = {"http": self.proxy, "https": self.proxy}
            
            url = f"https://kick.com/{username}"
            r = session.get(url, timeout=Config.REQUEST_TIMEOUT)
            
            Logger.info("📡", f"HTTP Status: {r.status_code}")
            
            if r.status_code == 200:
                Logger.status("⏳", "Rendering JavaScript", "15 seconds")
                r.html.render(timeout=15, wait=3, sleep=2)
                
                Logger.info("📏", f"Rendered content: {len(r.html.html):,} characters")
                
                content = r.html.html
                
                m3u8_links = re.findall(r'https?://[^\s"\'<>]*\.m3u8[^\s"\'<>]*', content)
                if m3u8_links:
                    Logger.success("✅", f"Found {len(m3u8_links)} m3u8 links in rendered content")
                    return m3u8_links[0]
                
                patterns = [
                    r'"playback_url":\s*"([^"]+)"',
                    r'"hls_url":\s*"([^"]+)"',
                    r'"stream_url":\s*"([^"]+)"',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        stream_url = match.group(1).replace('\\/', '/')
                        if stream_url.startswith('http'):
                            Logger.success("✅", "Pattern matched in rendered content")
                            return stream_url
            
            Logger.warning("❌", "No stream URL found in JavaScript rendering")
            return None
            
        except Exception as e:
            Logger.error("❌", f"JavaScript rendering failed: {str(e)[:50]}...")
            return None
    
    def _try_get_stream_url(self, url: str, is_mobile: bool = False) -> Optional[str]:
        """Single endpoint'ten stream URL alma - Enhanced Logging"""
        try:
            Logger.info("🌐", f"Connecting to: {url.split('/')[-2]}/{url.split('/')[-1]} {'(Mobile)' if is_mobile else '(Desktop)'}")
            
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            
            if not response:
                Logger.error("❌", "No response received")
                return None
                
            Logger.status("📡", "HTTP Status", str(response.status_code))
            Logger.status("📏", "Content Length", f"{len(response.text):,} chars")
            
            if response.status_code == 403:
                Logger.error("🚫", "403 Forbidden - Cloudflare protection detected")
                return None
            elif response.status_code == 404:
                Logger.error("🔍", "404 - Page not found")
                return None
            elif response.status_code != 200:
                Logger.error("❌", f"HTTP Error: {response.status_code}")
                return None
            
            content = response.text
            content_lower = content.lower()
            
            Logger.debug("🔍", "Analyzing page content...")
            
            if "offline" in content_lower:
                Logger.warning("📴", "Channel is offline")
                return None
            elif "not found" in content_lower or "channel not found" in content_lower:
                Logger.error("🔍", "Channel not found")
                return None
            elif "banned" in content_lower:
                Logger.error("🚫", "Channel is banned")
                return None
            
            live_indicators = ["live", "streaming", "online", "broadcasting"]
            found_live = [indicator for indicator in live_indicators if indicator in content_lower]
            if found_live:
                Logger.success("📺", f"Live indicators found: {', '.join(found_live)}")
            
            script_tags = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
            Logger.debug("📜", f"Found {len(script_tags)} script tags")
            
            for i, script in enumerate(script_tags):
                if 'm3u8' in script.lower() or 'playback' in script.lower():
                    Logger.info("🎯", f"Stream keywords found in script #{i+1}")
            
            data_attrs = re.findall(r'data-[^=]*=["\']([^"\']*)["\']', content)
            stream_data = [attr for attr in data_attrs if 'http' in attr and ('m3u8' in attr or 'stream' in attr)]
            if stream_data:
                Logger.success("🎯", f"Stream found in data attributes: {len(stream_data)} URLs")
                return stream_data[0]
            a
            json_ld = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', content, re.DOTALL)
            for i, json_data in enumerate(json_ld):
                try:
                    parsed = json.loads(json_data)
                    Logger.debug("📋", f"JSON-LD #{i+1} found")
                    result = self._extract_from_json(parsed)
                    if result:
                        return result
                except:
                    pass
            
            meta_tags = re.findall(r'<meta[^>]*content=["\']([^"\']*)["\']', content)
            stream_meta = [meta for meta in meta_tags if 'http' in meta and ('m3u8' in meta or 'stream' in meta)]
            if stream_meta:
                Logger.success("🎯", f"Stream found in meta tags: {len(stream_meta)} URLs")
                return stream_meta[0]
            
            stream_keywords = ["playback_url", "hls_url", "m3u8", "livestream", "stream_url", "video_url"]
            found_keywords = [kw for kw in stream_keywords if kw in content_lower]
            if found_keywords:
                Logger.info("🔍", f"Stream keywords found: {', '.join(found_keywords)}")

            patterns = [
                # Standart patterns
                r'playback_url["\']:\s*["\']([^"\']+)',
                r'"playback_url":\s*"([^"]+)"',
                r'playback_url\\?["\']:\\?["\']([^\\\"\']+)',
                r'"playback_url":"([^"]+)"',
                r'playback_url:\s*"([^"]+)"',
                
                # Livestream nested
                r'"livestream":\s*{[^}]*"playback_url":\s*"([^"]+)"',
                r'"livestream"[^}]*playback_url[^"]*"([^"]+)"',
                
                # Alternative names
                r'hls_url["\']:\s*["\']([^"\']+)',
                r'"hls_url":\s*"([^"]+)"',
                r'"m3u8_url":\s*"([^"]+)"',
                r'"stream_url":\s*"([^"]+)"',
                r'"video_url":\s*"([^"]+)"',
                
                # Mobile specific
                r'"mobile_url":\s*"([^"]+)"',
                r'"adaptive_url":\s*"([^"]+)"',
                
                # More generic
                r'["\']([^"\']*\.m3u8[^"\']*)',
                r'"(https?://[^"]*\.m3u8[^"]*)"',
                
                # JavaScript patterns
                r'src:\s*["\']([^"\']*\.m3u8[^"\']*)',
                r'url:\s*["\']([^"\']*\.m3u8[^"\']*)',
                
                # JSON nested
                r'"url":\s*"([^"]*\.m3u8[^"]*)"',
                r'"source":\s*"([^"]*\.m3u8[^"]*)"',
            ]
            
            Logger.debug("🔍", f"Testing {len(patterns)} patterns...")
            
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, content)
                if matches:
                    Logger.info("🎯", f"Pattern #{i+1} matched: {len(matches)} results")
                    for j, match in enumerate(matches[:3]):  # İlk 3'ünü göster
                        clean_url = match.replace('\\/', '/').replace('\\\\', '\\')
                        
                        if clean_url.startswith('http') and ('m3u8' in clean_url or 'hls' in clean_url):
                            Logger.success("✅", f"Valid stream URL found!")
                            return clean_url
            
            Logger.warning("❌", "No patterns matched")
            
            m3u8_links = re.findall(r'https?://[^\s"\'<>]*\.m3u8[^\s"\'<>]*', content)
            if m3u8_links:
                Logger.success("🎯", f"Direct m3u8 links found: {len(m3u8_links)}")
                return m3u8_links[0]
            
            title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)
                Logger.debug("📄", f"Page title: {title[:50]}...")
            
            Logger.error("🚫", "No stream URL found after detailed analysis")
            return None
            
        except Exception as e:
            Logger.error("❌", f"URL fetch error: {str(e)[:50]}...")
            return None

class M3U8StreamHandler:
    def __init__(self, master_url: str, session: UltimateBypassSession):
        self.master_url = master_url
        self.session = session
        self.base_url = self._get_base_url(master_url)
        self.stop_event = threading.Event()
        self.playback_thread: Optional[threading.Thread] = None
        self.consecutive_failures = 0
        self.last_successful_segment = time.time()
        self.segments_played = 0
        
    def _get_base_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{os.path.dirname(parsed.path)}/"
    
    def _resolve_url(self, segment_url: str) -> str:
        if segment_url.startswith(('http://', 'https://')):
            return segment_url
        return urljoin(self.base_url, segment_url)
    
    def _fetch_playlist(self, url: str) -> Optional[m3u8.M3U8]:
        try:
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            if response and response.status_code == 200:
                return m3u8.loads(response.text)
        except Exception:
            pass
        return None
    
    def _get_lowest_quality_stream(self) -> Optional[str]:
        master_playlist = self._fetch_playlist(self.master_url)
        if not master_playlist:
            return None
        
        if not master_playlist.playlists:
            return self.master_url
        
        try:
            lowest_variant = min(
                master_playlist.playlists,
                key=lambda x: x.stream_info.bandwidth or float('inf')
            )
            return self._resolve_url(lowest_variant.uri)
        except Exception:
            return self.master_url
    
    def _fetch_segment_minimal(self, segment_url: str) -> bool:
        try:
            full_url = self._resolve_url(segment_url)
            
            # HEAD request ile hızlı kontrol
            try:
                response = self.session.get(full_url, timeout=(5, 10))
                if response and response.status_code == 200:
                    self.last_successful_segment = time.time()
                    self.consecutive_failures = 0
                    self.segments_played += 1
                    return True
            except Exception:
                pass
            
            self.consecutive_failures += 1
            return False
                
        except Exception:
            self.consecutive_failures += 1
            return False
    
    def _simulate_playback(self, media_playlist_url: str) -> None:
        if not viewer_counter.increment():
            return
        
        try:
            segment_index = 0
            while not self.stop_event.is_set():
                try:
                    media_playlist = self._fetch_playlist(media_playlist_url)
                    if not media_playlist or not media_playlist.segments:
                        time.sleep(random.uniform(1, 3))
                        continue
                    
                    if media_playlist.segments:
                        segment_count = len(media_playlist.segments)
                        if segment_count > 0:
                            segment_index = segment_index % segment_count
                            segment = media_playlist.segments[segment_index]
                            self._fetch_segment_minimal(segment.uri)
                            segment_index += 1
                    
                    if self.consecutive_failures >= Config.MAX_CONSECUTIVE_FAILURES:
                        time.sleep(random.uniform(3, 6))
                        self.consecutive_failures = 0
                    
                    if hasattr(media_playlist, 'is_endlist') and media_playlist.is_endlist:
                        break
                    
                    if time.time() - self.last_successful_segment > Config.STREAM_TIMEOUT:
                        break
                    
                    time.sleep(random.uniform(Config.PLAYBACK_INTERVAL - 1, Config.PLAYBACK_INTERVAL + 2))
                    
                except Exception:
                    time.sleep(random.uniform(1, 3))
                    continue
                    
        finally:
            viewer_counter.decrement()
    
    def start(self) -> bool:
        try:
            stream_url = self._get_lowest_quality_stream()
            if not stream_url:
                return False
            
            self.playback_thread = threading.Thread(
                target=self._simulate_playback,
                args=(stream_url,),
                daemon=True
            )
            self.playback_thread.start()
            return True
            
        except Exception:
            return False
    
    def stop(self) -> None:
        self.stop_event.set()
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2)

def create_stream_viewer(username: str, proxy_manager: SmartProxyManager) -> Optional[M3U8StreamHandler]:
    if viewer_counter.count >= viewer_counter.target * 1.5:
        return None
    
    start_time = time.time()
    proxy = proxy_manager.get_best_proxy()
    
    if not proxy:
        viewer_counter.increment_failed_creates()
        return None
    
    try:
        platform_client = MultiEndpointKickPlatform(proxy)
        stream_url = platform_client.get_stream_url(username)
        
        response_time = time.time() - start_time
        
        if not stream_url:
            proxy_manager.mark_proxy_result(proxy, False, response_time)
            viewer_counter.increment_failed_creates()
            return None
        
        stream_handler = M3U8StreamHandler(stream_url, platform_client.session)
        if stream_handler.start():
            proxy_manager.mark_proxy_result(proxy, True, response_time)
            viewer_counter.increment_successful_creates()
            return stream_handler
        else:
            proxy_manager.mark_proxy_result(proxy, False, response_time)
            viewer_counter.increment_failed_creates()
            return None
            
    except Exception:
        response_time = time.time() - start_time
        proxy_manager.mark_proxy_result(proxy, False, response_time)
        viewer_counter.increment_failed_creates()
        return None

def get_user_input() -> Tuple[str, str]:
    """Kullanıcı girişi al"""
    Logger.section("USER INPUT")
    
    username = input(f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}👤 Enter Kick channel username: {Style.RESET_ALL}").strip()
    
    Logger.info("📁", "Available proxy files:")
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    
    if txt_files:
        for i, file in enumerate(txt_files, 1):
            Logger.info("  ", f"{i}. {file}")
        
        while True:
            proxy_input = input(f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}📋 Enter proxy filename: {Style.RESET_ALL}").strip()
            if proxy_input in txt_files:
                proxy_file = proxy_input
                break
            try:
                index = int(proxy_input) - 1
                if 0 <= index < len(txt_files):
                    proxy_file = txt_files[index]
                    break
            except ValueError:
                pass
            Logger.error("❌", "Invalid selection")
    else:
        proxy_file = input(f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}📋 Enter proxy filename: {Style.RESET_ALL}").strip()
    
    return username, proxy_file

def test_ultimate_bypass(username: str) -> None:
    """Ultimate bypass test with enhanced logging"""
    Logger.header("ULTIMATE BYPASS TEST")
    
    methods_tested = []
    
    if TLS_CLIENT_AVAILABLE:
        methods_tested.append("✅ TLS-Client")
    else:
        methods_tested.append("❌ TLS-Client")
    
    if HTTPX_AVAILABLE:
        methods_tested.append("✅ HTTPX/HTTP2")
    else:
        methods_tested.append("❌ HTTPX/HTTP2")
    
    if CLOUDSCRAPER_AVAILABLE:
        methods_tested.append("✅ CloudScraper")
    else:
        methods_tested.append("❌ CloudScraper")
    
    if REQUESTS_HTML_AVAILABLE:
        methods_tested.append("✅ Requests-HTML")
    else:
        methods_tested.append("❌ Requests-HTML")
    
    methods_tested.append("✅ Requests")
    
    Logger.info("🔧", f"Available methods: {' | '.join(methods_tested)}")
    Logger.info("🌐", f"Test endpoints: {', '.join([ep.replace('https://', '') for ep in Config.KICK_ENDPOINTS])}")
    
    # Simple test first - basic connectivity
    Logger.section("CONNECTIVITY TEST")
    try:
        import socket
        socket.setdefaulttimeout(10)
        result = socket.getaddrinfo('kick.com', 443)
        Logger.success("✅", f"DNS resolution successful: {result[0][4][0]}")
    except Exception as e:
        Logger.error("❌", f"DNS resolution failed: {e}")
        Logger.warning("💡", "Please check your internet connection")
        return
    
    # Önce büyük streamer test et
    Logger.section("CHANNEL TESTING")
    Logger.info("💡", "Testing with popular streamers may yield better results")
    Logger.info("📺", "Popular channels: trainwreckstv, amouranth, xqc, buddha")
    
    # Test farklı kanallar
    test_channels = [username, "trainwreckstv", "amouranth"]
    
    for test_channel in test_channels:
        try:
            Logger.info("🧪", f"Testing channel: {test_channel}")
            
            session = UltimateBypassSession()
            platform = MultiEndpointKickPlatform()
            
            Logger.status("🔍", "Searching for stream URL")
            stream_url = platform.get_stream_url(test_channel)
            
            if stream_url:
                Logger.success("✅", f"Stream URL found for {test_channel}: {stream_url[:60]}...")
                if test_channel != username:
                    Logger.info("💡", f"{test_channel} works, issue may be with {username}")
                break
            else:
                Logger.error("❌", f"No stream URL found for {test_channel}")
                
        except Exception as e:
            Logger.error("❌", f"{test_channel} test failed: {str(e)[:50]}...")
    
    # Troubleshooting suggestions
    Logger.section("TROUBLESHOOTING")
    Logger.warning("🤖", "IF NONE WORK:")
    Logger.warning("", "This might be Cloudflare's strongest protection")
    Logger.warning("💡", "Solution options:")
    Logger.warning("", "1. Browser automation (Selenium + undetected-chromedriver)")
    Logger.warning("", "2. Tor network usage")
    Logger.warning("", "3. Different proxy provider (residential proxies)")
    Logger.warning("", "4. VPN + proxy combination")
    
    # Manual check suggestion
    Logger.section("MANUAL VERIFICATION")
    Logger.info("💾", "MANUAL CHECK:")
    Logger.info("", f"Open https://kick.com/{username} in browser")
    Logger.info("", "F12 > Network tab > filter 'm3u8'")
    Logger.info("", "If m3u8 links appear, channel is live")
    
    # JavaScript rendering test
    if REQUESTS_HTML_AVAILABLE:
        Logger.section("JAVASCRIPT RENDERING TEST")
        try:
            session = UltimateBypassSession()
            platform = MultiEndpointKickPlatform()
            result = platform._try_js_rendering(username)
            if result:
                Logger.success("✅", f"JS rendering found: {result[:60]}...")
            else:
                Logger.error("❌", "JS rendering also failed")
        except Exception as e:
            Logger.error("❌", f"JS rendering test failed: {str(e)[:50]}...")
    
    Logger.info("🤔", "Based on test results, browser automation may be needed")
    Logger.info("🔧", "Would you like to use Selenium + undetected-chromedriver?")

def cleanup_resources(handlers: List[M3U8StreamHandler]) -> None:
    for handler in handlers:
        try:
            handler.stop()
        except Exception:
            pass

def signal_handler(signum, frame):
    Logger.warning("🛑", "Interrupt signal received, shutting down...")
    sys.exit(0)

def print_stats(batch_counter: int, proxy_manager: SmartProxyManager):
    """Enhanced statistics display"""
    current_count = viewer_counter.count
    target = viewer_counter.target
    uptime = viewer_counter.uptime
    successful = viewer_counter.successful_creates
    failed = viewer_counter.failed_creates
    challenges = viewer_counter.cloudflare_challenges
    tls_bypasses = viewer_counter.tls_bypasses
    mobile_requests = viewer_counter.mobile_requests
    js_renders = viewer_counter.js_renders
    
    efficiency = (current_count / target * 100) if target > 0 else 0
    success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
    proxy_success_rate = proxy_manager.avg_success_rate
    
    # stats display
    print(f"\n{Fore.LIGHTGREEN_EX}{Style.BRIGHT}╔══════════════════════════════════════════════════════════════════════════════╗")
    print(f"║{' '*32}BATCH #{batch_counter:,} STATISTICS{' '*32}║")
    print(f"╠══════════════════════════════════════════════════════════════════════════════╣")
    print(f"║ {Fore.LIGHTCYAN_EX}👥 VIEWERS:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {current_count:,}/{target:,} ({efficiency:.1f}%){' '*(25-len(f'{current_count:,}/{target:,} ({efficiency:.1f}%)'))}║")
    print(f"║ {Fore.LIGHTYELLOW_EX}📊 SUCCESS RATE:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {success_rate:.1f}%{' '*(35-len(f'{success_rate:.1f}%'))}║")
    print(f"║ {Fore.LIGHTMAGENTA_EX}🌐 PROXY SUCCESS:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {proxy_success_rate:.1f}%{' '*(34-len(f'{proxy_success_rate:.1f}%'))}║")
    print(f"╠══════════════════════════════════════════════════════════════════════════════╣")
    print(f"║ {Fore.LIGHTBLUE_EX}🔐 TLS BYPASSES:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {tls_bypasses:,}{' '*(35-len(f'{tls_bypasses:,}'))}║")
    print(f"║ {Fore.LIGHTRED_EX}⚡ CF CHALLENGES:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {challenges:,}{' '*(34-len(f'{challenges:,}'))}║")
    print(f"║ {Fore.LIGHTCYAN_EX}📱 MOBILE REQUESTS:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {mobile_requests:,}{' '*(32-len(f'{mobile_requests:,}'))}║")
    print(f"║ {Fore.LIGHTYELLOW_EX}🎭 JS RENDERS:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {js_renders:,}{' '*(37-len(f'{js_renders:,}'))}║")
    print(f"╠══════════════════════════════════════════════════════════════════════════════╣")
    print(f"║ {Fore.LIGHTMAGENTA_EX}🚫 FAILED PROXIES:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {proxy_manager.failed_proxy_count:,}/{proxy_manager.total_proxies:,}{' '*(25-len(f'{proxy_manager.failed_proxy_count:,}/{proxy_manager.total_proxies:,}'))}║")
    print(f"║ {Fore.LIGHTCYAN_EX}⏱️  UPTIME:{Style.RESET_ALL}{Fore.LIGHTGREEN_EX} {uptime}s{' '*(43-len(f'{uptime}s'))}║")
    print(f"╚══════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    Logger.header("KICK VIEWER BOT - ULTIMATE BYPASS")
    
    capabilities = []
    if TLS_CLIENT_AVAILABLE:
        capabilities.append("🔐 TLS-Client")
    if HTTPX_AVAILABLE:
        capabilities.append("🌐 HTTP/2")
    if CLOUDSCRAPER_AVAILABLE:
        capabilities.append("⚡ CloudFlare")
    if REQUESTS_HTML_AVAILABLE:
        capabilities.append("🎭 JS-Render")
    
    capabilities.append("📱 Mobile-Endpoints")
    capabilities.append("🧠 Smart-Proxy")
    
    Logger.section("ULTIMATE BYPASS CAPABILITIES")
    for cap in capabilities:
        Logger.success("✅", cap)
    
    if len(capabilities) < 6:
        Logger.section("ENHANCEMENT SUGGESTIONS")
        Logger.warning("💡", "For stronger bypass capabilities:")
        if not TLS_CLIENT_AVAILABLE:
            Logger.warning("", "pip install tls-client")
        if not HTTPX_AVAILABLE:
            Logger.warning("", "pip install httpx[http2]")
        if not CLOUDSCRAPER_AVAILABLE:
            Logger.warning("", "pip install cloudscraper")
        if not REQUESTS_HTML_AVAILABLE:
            Logger.warning("", "pip install requests-html")
    
    try:
        username, proxy_file = get_user_input()
        
        # Ultimate bypass test
        test_ultimate_bypass(username)
        
        proxy_manager = SmartProxyManager(proxy_file)
        
        if not proxy_manager.total_proxies:
            Logger.error("❌", f"No valid proxies loaded from {proxy_file}")
            return
        
        # Devam etmek istiyor mu?
        choice = input(f"\n{Fore.LIGHTCYAN_EX}{Style.BRIGHT}🤔 Continue with ultimate bypass? (y/n): {Style.RESET_ALL}").lower()
        if choice != 'y':
            Logger.warning("⏹️", "Operation cancelled")
            return
        
        # Ayarlar
        target_viewers = int(proxy_manager.total_proxies * Config.VIEWERS_PER_PROXY * Config.TARGET_MULTIPLIER)
        max_threads = min(Config.MAX_CONCURRENT_THREADS, target_viewers)
        batch_size = Config.BATCH_SIZE
        
        Logger.section("ULTIMATE BYPASS CONFIGURATION")
        Logger.success("📊", f"Smart Proxies: {proxy_manager.total_proxies:,}")
        Logger.success("🎯", f"Target Viewers: {target_viewers:,}")
        Logger.success("🧵", f"Max Threads: {max_threads:,}")
        Logger.success("📦", f"Batch Size: {batch_size:,}")
        Logger.success("⚡", "Mode: ULTIMATE BYPASS KILLER")
        
        viewer_counter.set_target(target_viewers)
        active_handlers: List[M3U8StreamHandler] = []
        atexit.register(cleanup_resources, active_handlers)
        
        Logger.header("ULTIMATE BYPASS KILLER STARTING")
        
        batch_counter = 0
        
        while True:
            try:
                batch_counter += 1
                current_viewers = viewer_counter.count
                
                if current_viewers < target_viewers:
                    needed = target_viewers - current_viewers
                    current_batch_size = min(batch_size, needed, max_threads)
                    
                    if current_batch_size > 0:
                        Logger.info("🚀", f"Creating {current_batch_size:,} new viewers...")
                        
                        with ThreadPoolExecutor(max_workers=min(current_batch_size, 80)) as executor:
                            futures = [
                                executor.submit(create_stream_viewer, username, proxy_manager)
                                for _ in range(current_batch_size)
                            ]
                            
                            completed = 0
                            for future in as_completed(futures, timeout=90):
                                try:
                                    handler = future.result(timeout=15)
                                    if handler:
                                        active_handlers.append(handler)
                                    completed += 1
                                    
                                    # Progress bar
                                    Logger.progress(completed, current_batch_size, "Progress:", f"{completed}/{current_batch_size}")
                                except Exception:
                                    pass
                            
                            print()  # New line after progress bar
                
                active_handlers = [h for h in active_handlers 
                                 if h.playback_thread and h.playback_thread.is_alive()]

                if batch_counter % 3 == 0 or batch_counter <= Config.RAPID_START_BATCHES:
                    print_stats(batch_counter, proxy_manager)
                
                time.sleep(Config.MAINTENANCE_INTERVAL)
                
            except KeyboardInterrupt:
                Logger.warning("⏹️", "ULTIMATE BYPASS KILLER STOPPED")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(8)
                continue
        
    except Exception as e:
        Logger.error("❌", f"ULTIMATE BYPASS ERROR: {str(e)[:50]}...")
        logger.error(f"Application error: {e}")
    
    finally:
        Logger.header("ULTIMATE BYPASS KILLER SHUTDOWN COMPLETE")

if __name__ == "__main__":
    main()