import requests
import feedparser
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import streamlit as st
from urllib.parse import quote_plus
import time

logger = logging.getLogger(__name__)

class NewsSource:
    """Individual news source configuration"""
    def __init__(self, name: str, rss_url: str, base_url: Optional[str] = None):
        self.name = name
        self.rss_url = rss_url
        self.base_url = base_url

class FinanceNewsFetcher:
    """
    Fetches financial news from multiple sources
    """
    
    # Popular financial news sources
    NEWS_SOURCES = {
        'yahoo_finance': NewsSource(
            name="Yahoo Finance",
            rss_url="https://feeds.finance.yahoo.com/rss/2.0/headline",
            base_url="https://finance.yahoo.com"
        ),
        'reuters_business': NewsSource(
            name="Reuters Business",
            rss_url="https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
            base_url="https://www.reuters.com"
        ),
        'marketwatch': NewsSource(
            name="MarketWatch",
            rss_url="http://feeds.marketwatch.com/marketwatch/marketpulse/",
            base_url="https://www.marketwatch.com"
        ),
        'cnbc': NewsSource(
            name="CNBC",
            rss_url="https://www.cnbc.com/id/100003114/device/rss/rss.html",
            base_url="https://www.cnbc.com"
        ),
        'bloomberg': NewsSource(
            name="Bloomberg",
            rss_url="https://feeds.bloomberg.com/markets/news.rss",
            base_url="https://www.bloomberg.com"
        )
    }
    
    def __init__(self):
        self.cache_duration = 300  # 5 minutes cache
        
    @st.cache_data(ttl=300)
    def _fetch_rss_feed(_self, source_name: str, url: str) -> List[Dict]:
        """Fetch and parse RSS feed from a news source"""
        try:
            # Set user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Parse RSS feed
            feed = feedparser.parse(url, request_headers=headers)
            
            if feed.bozo:
                logger.warning(f"RSS feed parsing warning for {source_name}: {feed.bozo_exception}")
            
            articles = []
            for entry in feed.entries[:10]:  # Limit to 10 most recent articles
                try:
                    # Parse publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    else:
                        pub_date = datetime.now()
                    
                    # Extract summary/description
                    summary = ""
                    if hasattr(entry, 'summary'):
                        summary = entry.summary
                    elif hasattr(entry, 'description'):
                        summary = entry.description
                    
                    # Clean HTML tags from summary
                    import re
                    summary = re.sub('<[^<]+?>', '', summary)
                    summary = summary.strip()[:300] + "..." if len(summary) > 300 else summary
                    
                    article = {
                        'title': entry.title if hasattr(entry, 'title') else 'No Title',
                        'link': entry.link if hasattr(entry, 'link') else '',
                        'summary': summary,
                        'published': pub_date,
                        'source': source_name,
                        'author': getattr(entry, 'author', 'Unknown')
                    }
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Error parsing article from {source_name}: {str(e)}")
                    continue
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed from {source_name}: {str(e)}")
            return []
    
    def get_market_news(self, sources: Optional[List[str]] = None, limit: int = 20) -> List[Dict]:
        """
        Get latest market news from specified sources
        """
        if sources is None:
            sources = ['yahoo_finance', 'reuters_business', 'marketwatch']
        
        all_articles = []
        
        for source_key in sources:
            if source_key in self.NEWS_SOURCES:
                source = self.NEWS_SOURCES[source_key]
                articles = self._fetch_rss_feed(source.name, source.rss_url)
                all_articles.extend(articles)
            else:
                logger.warning(f"Unknown news source: {source_key}")
        
        # Sort by publication date (newest first)
        all_articles.sort(key=lambda x: x['published'], reverse=True)
        
        return all_articles[:limit]
    
    def get_symbol_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        Get news specific to a symbol/company
        """
        try:
            # Use Yahoo Finance symbol-specific RSS
            symbol_clean = symbol.replace('^', '').replace('.', '-')
            yahoo_symbol_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol_clean}&region=US&lang=en-US"
            
            articles = self._fetch_rss_feed(f"Yahoo Finance ({symbol})", yahoo_symbol_url)
            
            # Filter articles that mention the symbol
            filtered_articles = []
            for article in articles:
                if (symbol.upper() in article['title'].upper() or 
                    symbol.upper() in article['summary'].upper()):
                    filtered_articles.append(article)
            
            return filtered_articles[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching symbol news for {symbol}: {str(e)}")
            return []
    
    def get_sector_news(self, sector: str, limit: int = 10) -> List[Dict]:
        """
        Get news for a specific sector
        """
        sector_keywords = {
            'technology': ['tech', 'technology', 'software', 'artificial intelligence', 'AI'],
            'healthcare': ['healthcare', 'pharma', 'biotech', 'medical'],
            'finance': ['banking', 'finance', 'fintech', 'insurance'],
            'energy': ['energy', 'oil', 'gas', 'renewable', 'solar'],
            'retail': ['retail', 'consumer', 'shopping', 'e-commerce']
        }
        
        keywords = sector_keywords.get(sector.lower(), [sector])
        
        # Get general market news and filter
        all_articles = self.get_market_news(limit=50)
        sector_articles = []
        
        for article in all_articles:
            text = (article['title'] + ' ' + article['summary']).lower()
            if any(keyword.lower() in text for keyword in keywords):
                sector_articles.append(article)
        
        return sector_articles[:limit]
    
    def get_trending_topics(self) -> List[Dict]:
        """
        Get trending financial topics based on news frequency
        """
        try:
            # Get recent news
            articles = self.get_market_news(limit=50)
            
            # Extract keywords and count frequency
            keyword_counts: dict[str, int] = {}
            common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'a', 'an'}
            
            for article in articles:
                words = article['title'].lower().split()
                for word in words:
                    # Clean word
                    word = ''.join(c for c in word if c.isalnum())
                    if len(word) > 3 and word not in common_words:
                        keyword_counts[word] = keyword_counts.get(word, 0) + 1
            
            # Sort by frequency
            trending = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
            
            return [{'topic': topic, 'count': count} for topic, count in trending[:10]]
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {str(e)}")
            return []
    
    def search_news(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for news articles containing specific terms
        """
        try:
            # Get general news and filter by query
            all_articles = self.get_market_news(limit=100)
            matching_articles = []
            
            query_lower = query.lower()
            
            for article in all_articles:
                text = (article['title'] + ' ' + article['summary']).lower()
                if query_lower in text:
                    # Calculate relevance score based on query matches
                    title_matches = article['title'].lower().count(query_lower)
                    summary_matches = article['summary'].lower().count(query_lower)
                    article['relevance'] = title_matches * 2 + summary_matches
                    matching_articles.append(article)
            
            # Sort by relevance and recency
            matching_articles.sort(key=lambda x: (x['relevance'], x['published']), reverse=True)
            
            return matching_articles[:limit]
            
        except Exception as e:
            logger.error(f"Error searching news for '{query}': {str(e)}")
            return []
    
    def get_available_sources(self) -> Dict[str, str]:
        """Get list of available news sources"""
        return {key: source.name for key, source in self.NEWS_SOURCES.items()}
    
    def format_article_for_display(self, article: Dict) -> str:
        """Format article for display in Streamlit"""
        time_ago = self._time_ago(article['published'])
        
        return f"""
        **{article['title']}**  
        *{article['source']} • {time_ago}*  
        {article['summary']}  
        [Read more]({article['link']})
        """
    
    def _time_ago(self, pub_date: datetime) -> str:
        """Calculate human-readable time difference"""
        now = datetime.now()
        diff = now - pub_date
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"

# Initialize news fetcher
news_fetcher = FinanceNewsFetcher()
