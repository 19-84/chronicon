// Search functionality - Phase 3 implementation

class ForumSearch {
    constructor(indexPath) {
        this.index = null;
        this.loadIndex(indexPath);
    }

    async loadIndex(path) {
        try {
            const response = await fetch(path);
            this.index = await response.json();
            console.log('Search index loaded:', this.index.items.length, 'items');
        } catch (error) {
            console.error('Failed to load search index:', error);
        }
    }

    search(query) {
        if (!this.index || !query) {
            return [];
        }

        const results = [];
        const queryLower = query.toLowerCase();

        for (const item of this.index.items) {
            const titleMatch = item.title && item.title.toLowerCase().includes(queryLower);
            const contentMatch = item.excerpt && item.excerpt.toLowerCase().includes(queryLower);

            if (titleMatch || contentMatch) {
                results.push(item);
            }
        }

        return results;
    }

    displayResults(results) {
        const container = document.getElementById('search-results');
        if (!container) return;

        if (results.length === 0) {
            container.innerHTML = '<p>No results found.</p>';
            return;
        }

        const html = results.map(item => `
            <div class="search-result">
                <h3><a href="${item.url}">${item.title}</a></h3>
                <p class="excerpt">${item.excerpt}</p>
                <p class="meta">
                    <span class="author">${item.author}</span> -
                    <span class="date">${item.created_at}</span>
                </p>
            </div>
        `).join('');

        container.innerHTML = html;
    }
}

// Initialize search when page loads
document.addEventListener('DOMContentLoaded', () => {
    const searcher = new ForumSearch('search_index.json');

    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');

    if (searchButton) {
        searchButton.addEventListener('click', () => {
            const query = searchInput.value;
            const results = searcher.search(query);
            searcher.displayResults(results);
        });
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const results = searcher.search(searchInput.value);
                searcher.displayResults(results);
            }
        });
    }
});
