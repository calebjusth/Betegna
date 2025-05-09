document.addEventListener('DOMContentLoaded', function() {
    // Handle all add-to-cart forms
    document.querySelectorAll('form[action*="/cart/add/"]').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const button = this.querySelector('button');
            const originalText = button.innerHTML;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
            button.disabled = true;
            
            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': this.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: new FormData(this)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Update cart count
                    const cartCountElements = document.querySelectorAll('.cart-count');
                    cartCountElements.forEach(el => {
                        el.textContent = data.cart_count;
                    });
                    
                    // Show success message (you can replace this with a toast)
                    alert(data.message);
                } else {
                    alert('Failed to add to cart');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred');
            } finally {
                button.innerHTML = originalText;
                button.disabled = false;
            }
        });
    });
});

// Search functionality
document.addEventListener('DOMContentLoaded', function() {
const searchInput = document.getElementById('search-input');
const searchResultsContainer = document.getElementById('search-results-container');
const searchResults = document.querySelector('.search-results');
const searchIcon = document.getElementById('search-icon');

let searchTimeout;

// Fetch search results
function fetchSearchResults(query) {
    if (query.length < 2) {
        searchResultsContainer.style.display = 'none';
        return;
    }
    
    fetch(`/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            if (data.results.length > 0) {
                let html = '';
                data.results.forEach(product => {
                    html += `
                        <a href="/product/${product.slug}/" class="search-result-item">
                            <img src="${product.image}" alt="${product.name}">
                            <div class="info">
                                <div class="name">${product.name}</div>
                                <div class="category">${product.category_name}</div>
                            </div>
                            <div class="price">$${product.price}</div>
                        </a>
                    `;
                });
                
                // Add "View all results" link
                html += `
                    <div class="search-result-item view-all">
                        <a href="/search/?q=${encodeURIComponent(query)}" class="view-all-link">
                            View all ${data.results.length} results for "${query}"
                        </a>
                    </div>
                `;
                
                searchResults.innerHTML = html;
                searchResultsContainer.style.display = 'block';
            } else {
                searchResults.innerHTML = '<div class="no-results">No products found. Try different keywords.</div>';
                searchResultsContainer.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

// Event listeners
searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        fetchSearchResults(this.value.trim());
    }, 300);
});

searchIcon.addEventListener('click', function() {
    if (searchInput.value.trim()) {
        window.location.href = `/search/?q=${encodeURIComponent(searchInput.value.trim())}`;
    }
});

searchInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && this.value.trim()) {
        window.location.href = `/search/?q=${encodeURIComponent(this.value.trim())}`;
    }
});

// Close search results when clicking outside
document.addEventListener('click', function(e) {
    if (!searchResultsContainer.contains(e.target) && e.target !== searchInput) {
        searchResultsContainer.style.display = 'none';
    }
});
});





(function() {
    // API Configuration
    const GEO_API = 'https://ipapi.co/json/';
    const RATE_API = 'https://api.exchangerate-api.com/v4/latest/USD';
    const CURRENCY_SYMBOLS = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 
        'CAD': 'CA$', 'AUD': 'AU$', 'CNY': '¥', 'ETB': 'Br'
    };

    // Cache for 24 hours (in milliseconds)
    const CACHE_DURATION = 24 * 60 * 60 * 1000;
    const CACHE_KEY = 'currency_data';

    // Format number with commas
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    // Get cached data
    function getCachedData() {
        const cached = localStorage.getItem(CACHE_KEY);
        if (!cached) return null;
        
        const { timestamp, data } = JSON.parse(cached);
        if (Date.now() - timestamp > CACHE_DURATION) return null;
        
        return data;
    }

    // Save to cache
    function cacheData(data) {
        localStorage.setItem(CACHE_KEY, JSON.stringify({
            timestamp: Date.now(),
            data: data
        }));
    }

    async function convertPrices() {
        try {
            // Check cache first
            const cached = getCachedData();
            let currency, rate;

            if (cached) {
                ({ currency, rate } = cached);
            } else {
                // Get user location and currency
                const geoResp = await fetch(GEO_API);
                const geo = await geoResp.json();
                currency = geo.currency || 'USD';

                // Get exchange rates
                const rateResp = await fetch(RATE_API);
                const rates = await rateResp.json();
                rate = rates.rates[currency];

                // Cache the data
                if (rate) {
                    cacheData({ currency, rate });
                } else {
                    console.warn(`No exchange rate found for ${currency}`);
                    return;
                }
            }

            // Convert all price elements
            document.querySelectorAll('.price').forEach(el => {
                const baseAmount = parseFloat(el.dataset.base);
                if (isNaN(baseAmount)) return;
                
                const converted = (baseAmount * rate).toFixed(2);
                const symbol = CURRENCY_SYMBOLS[currency] || currency + ' ';
                const formattedValue = formatNumber(converted);
                
                el.textContent = `${symbol}${formattedValue}`;
                el.dataset.converted = converted;
                el.dataset.currency = currency;
            });

            // Dispatch event for other scripts
            document.dispatchEvent(new CustomEvent('currencyConverted', {
                detail: { currency, rate }
            }));

        } catch (e) {
            console.error('Currency conversion error:', e);
            // Fallback to original prices
            document.querySelectorAll('.price').forEach(el => {
                const baseAmount = parseFloat(el.dataset.base);
                if (!isNaN(baseAmount)) {
                    el.textContent = `$${formatNumber(baseAmount.toFixed(2))}`;
                }
            });
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', convertPrices);
    } else {
        convertPrices();
    }

    // Optional: Add currency switcher functionality
    function createCurrencySwitcher() {
        const container = document.createElement('div');
        container.className = 'currency-switcher';
        container.innerHTML = `
            <select class="currency-selector">
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
                <option value="ETB">ETB (Br)</option>
                <!-- Add more currencies as needed -->
            </select>
        `;
        
        document.body.appendChild(container);
        
        const selector = container.querySelector('.currency-selector');
        selector.addEventListener('change', async (e) => {
            const currency = e.target.value;
            const rateResp = await fetch(RATE_API);
            const rates = await rateResp.json();
            const rate = rates.rates[currency];
            
            if (rate) {
                document.querySelectorAll('.price').forEach(el => {
                    const baseAmount = parseFloat(el.dataset.base);
                    if (isNaN(baseAmount)) return;
                    
                    const converted = (baseAmount * rate).toFixed(2);
                    const symbol = CURRENCY_SYMBOLS[currency] || currency + ' ';
                    el.textContent = `${symbol}${formatNumber(converted)}`;
                    el.dataset.converted = converted;
                    el.dataset.currency = currency;
                });
                
                // Update cache with new selection
                cacheData({ currency, rate });
            }
        });
    }

    // Uncomment to enable currency switcher
    // createCurrencySwitcher();
})();




