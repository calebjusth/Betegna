from django.db.models import Count, Q
from .models import UserInteraction, Product
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
import json
from datetime import datetime, timedelta
from django.core.cache import cache
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self):
        # Cache for product similarities
        self.product_similarity_cache = None
        self.last_similarity_update = None
        # Cache timeout in seconds (15 minutes)
        self.cache_timeout = 60 * 15
    
    def get_recommendations(self, request, limit: int = 12) -> Optional[List[Product]]:
        """Main method to get recommendations for a user/session"""
        # Generate cache key
        cache_key = self._get_cache_key(request)
        
        # Try to get cached recommendations
        cached_recommendations = cache.get(cache_key)
        if cached_recommendations:
            logger.debug("Returning cached recommendations")
            return cached_recommendations
        
        if request.user.is_authenticated:
            user_id = request.user.id
            session_key = None
        else:
            user_id = None
            session_key = request.session.session_key
        
        # Get recent user interactions
        recent_interactions = self.get_user_interactions(user_id, session_key)
        
        if not recent_interactions:
            logger.debug("No recent interactions, returning None")
            return None
            
        try:
            # Get different types of recommendations
            content_based_recs = self.get_content_based_recommendations(recent_interactions, limit)
            collaborative_recs = self.get_collaborative_recommendations(recent_interactions, limit)
            search_based_recs = self.get_search_based_recommendations(recent_interactions, limit)
            
            # Combine recommendations
            combined = self.combine_recommendations(
                content_based_recs,
                collaborative_recs,
                search_based_recs,
                limit=limit
            )
            
            # Cache the results
            cache.set(cache_key, combined, self.cache_timeout)
            logger.debug(f"Cached recommendations for key: {cache_key}")
            
            return combined
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}", exc_info=True)
            return None

    def _get_cache_key(self, request) -> str:
        """Generate cache key based on user/session"""
        if request.user.is_authenticated:
            return f"user_recs:{request.user.id}"
        return f"session_recs:{request.session.session_key}"

    def combine_recommendations(self, 
                              content_recs: List[Product], 
                              collaborative_recs: List[Product], 
                              search_recs: List[Product], 
                              limit: int = 12) -> List[Product]:
        """Combine different recommendation types with weights"""
        combined = []
        weights = [0.5, 0.3, 0.2]  # Weights for content, collaborative, search
        
        # Add content-based recommendations
        for product in content_recs:
            combined.append((product, weights[0]))
        
        # Add collaborative recommendations
        for product in collaborative_recs:
            combined.append((product, weights[1]))
        
        # Add search-based recommendations
        for product in search_recs:
            combined.append((product, weights[2]))
        
        # Group by product and sum weights
        product_weights = defaultdict(float)
        for product, weight in combined:
            product_weights[product] += weight
            
        # Sort by combined weight and return top results
        return [
            p for p, w in sorted(
                product_weights.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:limit]
        ]
    
    def get_user_interactions(self, user_id: Optional[int], session_key: Optional[str], days: int = 30) -> List[UserInteraction]:
        """Get recent user interactions"""
        time_threshold = datetime.now() - timedelta(days=days)
        filters = {
            'timestamp__gte': time_threshold
        }
        
        if user_id:
            filters['user_id'] = user_id
        elif session_key:
            filters['session_key'] = session_key
        else:
            return []
            
        return list(UserInteraction.objects.filter(**filters).select_related('product'))
    
    def get_content_based_recommendations(self, interactions: List[UserInteraction], limit: int) -> List[Product]:
        """Recommend similar products based on category/attributes"""
        if not interactions:
            return []
            
        # Get all viewed product categories and IDs
        viewed_categories = set()
        viewed_products = set()
        
        for interaction in interactions:
            if interaction.product:  # Ensure product exists
                viewed_categories.add(interaction.product.category)
                viewed_products.add(interaction.product.id)
        
        if not viewed_categories:
            return []
        
        # Get similar products from these categories
        similar_products = Product.objects.filter(
            category__in=viewed_categories,
            is_active=True
        ).exclude(
            id__in=viewed_products
        ).order_by('?')[:limit*3]  # Get extra to allow for filtering
        
        if not similar_products:
            return []
        
        # Prepare descriptions for similarity calculation
        product_descriptions = {p.id: p.description for p in similar_products if p.description}
        viewed_product_descriptions = {
            p.product.id: p.product.description 
            for p in interactions 
            if p.product and p.product.description
        }
        
        all_descriptions = {**product_descriptions, **viewed_product_descriptions}
        if not all_descriptions:
            return list(similar_products)[:limit]
        
        try:
            # Create TF-IDF vectors and calculate similarities
            vectorizer = TfidfVectorizer(stop_words='english')
            desc_list = [all_descriptions[pid] for pid in all_descriptions]
            tfidf_matrix = vectorizer.fit_transform(desc_list)
            cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
            
            # Generate recommendations based on similarity
            recommendations = []
            viewed_ids = list(viewed_product_descriptions.keys())
            
            for viewed_id in viewed_ids:
                viewed_idx = list(all_descriptions.keys()).index(viewed_id)
                sim_scores = list(enumerate(cosine_sim[viewed_idx]))
                sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
                
                # Get top similar items (excluding itself)
                for i, score in sim_scores[1:6]:  # Top 5 similar per viewed item
                    product_id = list(all_descriptions.keys())[i]
                    if product_id not in viewed_ids and product_id in product_descriptions:
                        recommendations.append((product_id, score))
            
            # Sort and get unique products
            recommendations.sort(key=lambda x: x[1], reverse=True)
            seen = set()
            unique_recs = []
            
            for pid, score in recommendations:
                if pid not in seen:
                    seen.add(pid)
                    unique_recs.append(pid)
                    if len(unique_recs) >= limit:
                        break
            
            # Get full product objects
            products = Product.objects.filter(id__in=unique_recs, is_active=True)
            product_map = {p.id: p for p in products}
            
            return [product_map[pid] for pid in unique_recs if pid in product_map]
            
        except Exception as e:
            logger.error(f"Content-based recommendation error: {str(e)}", exc_info=True)
            return list(similar_products)[:limit]
    
    def get_collaborative_recommendations(self, interactions: List[UserInteraction], limit: int) -> List[Product]:
        """Recommend products based on what similar users viewed"""
        if not interactions:
            return []
            
        # Get products this user has interacted with
        user_product_ids = {i.product.id for i in interactions if i.product}
        
        if not user_product_ids:
            return []
        
        # Find other users who viewed the same products
        similar_users = UserInteraction.objects.filter(
            product_id__in=user_product_ids
        ).exclude(
            user=interactions[0].user if interactions[0].user else None,
            session_key=interactions[0].session_key if not interactions[0].user else ''
        ).values('user', 'session_key').annotate(
            common_products=Count('product')
        ).order_by('-common_products')[:10]  # Top 10 similar users
        
        if not similar_users:
            return []
            
        # Get products those users viewed (that our user hasn't)
        recommended_products = UserInteraction.objects.filter(
            Q(user__in=[u['user'] for u in similar_users if u['user']]) |
            Q(session_key__in=[u['session_key'] for u in similar_users if u['session_key']])
        ).exclude(
            product_id__in=user_product_ids
        ).values('product').annotate(
            popularity=Count('product')
        ).order_by('-popularity')[:limit]
        
        product_ids = [r['product'] for r in recommended_products]
        return list(Product.objects.filter(id__in=product_ids, is_active=True))
    
    def get_search_based_recommendations(self, interactions: List[UserInteraction], limit: int) -> List[Product]:
        """Recommend products based on search queries"""
        recent_searches = [
            i.search_query for i in interactions 
            if i.search_query and i.interaction_type == 'search_click'
        ]
        
        if not recent_searches:
            return []
            
        # Find products that match these search terms
        query = Q()
        for term in recent_searches:
            if term.strip():  # Skip empty terms
                query |= Q(name__icontains=term) | Q(description__icontains=term)
                
        return list(Product.objects.filter(query, is_active=True).order_by('?')[:limit])