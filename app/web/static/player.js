/**
 * CiteCast Player JavaScript
 * Handles the interactive media player with citation sidebar
 */

class CiteCastPlayer {
    constructor(config) {
        this.container = config.container || document.getElementById('player-container');
        this.sidebar = config.sidebar || document.getElementById('citation-sidebar');
        this.scenes = config.scenes || [];
        this.currentIndex = 0;
        this.isPlaying = false;
        this.autoPlay = config.autoPlay || false;
        
        this.init();
    }
    
    init() {
        this.renderSceneMarkers();
        this.updateScene(0);
        this.bindEvents();
    }
    
    renderSceneMarkers() {
        const markersContainer = this.container.querySelector('.scene-markers');
        if (!markersContainer) return;
        
        markersContainer.innerHTML = this.scenes.map((scene, index) => `
            <div class="scene-marker" data-index="${index}" 
                 title="${scene.claim_text || 'Scene ' + (index + 1)}"
                 style="flex: 1; height: 4px; background: rgba(255,255,255,0.3); border-radius: 2px; cursor: pointer;">
            </div>
        `).join('');
    }
    
    updateScene(index) {
        if (index < 0 || index >= this.scenes.length) return;
        
        this.currentIndex = index;
        const scene = this.scenes[index];
        
        // Update image
        const imageElement = this.container.querySelector('.scene-image');
        if (imageElement && scene.image_url) {
            imageElement.src = scene.image_url;
        }
        
        // Update citation sidebar
        this.updateCitations(scene);
        
        // Update markers
        this.updateMarkers(index);
        
        // Update counter
        const counter = this.container.querySelector('.scene-counter');
        if (counter) {
            counter.textContent = `Scene ${index + 1} / ${this.scenes.length}`;
        }
    }
    
    updateCitations(scene) {
        const sidebar = this.sidebar;
        if (!sidebar) return;
        
        // Update claim text
        const claimElement = sidebar.querySelector('.current-claim');
        if (claimElement) {
            claimElement.textContent = scene.claim_text || 'No claim available';
        }
        
        // Update citations list
        const citationsList = sidebar.querySelector('.citations-list');
        if (citationsList) {
            if (!scene.citations || scene.citations.length === 0) {
                citationsList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-info-circle"></i>
                        <p>No citations for this scene.</p>
                    </div>
                `;
                return;
            }
            
            citationsList.innerHTML = scene.citations.map(c => `
                <div class="citation-item fade-in">
                    <div class="citation-header">
                        <span class="citation-page">📄 Page ${c.page || 'N/A'}</span>
                        <span class="citation-confidence ${c.confidence_level || 'medium'}">
                            ${c.confidence_level || 'unknown'}
                        </span>
                    </div>
                    <div class="citation-text">
                        <blockquote>“${c.text_preview || 'No preview available'}"</blockquote>
                    </div>
                    ${c.section_title ? `<div class="citation-section">Section: ${c.section_title}</div>` : ''}
                    <div class="citation-score">Match: ${Math.round((c.similarity_score || 0) * 100)}%</div>
                </div>
            `).join('');
        }
        
        // Update citation count
        const countElement = sidebar.querySelector('.citation-count');
        if (countElement) {
            countElement.textContent = `${scene.citations ? scene.citations.length : 0} citations`;
        }
    }
    
    updateMarkers(activeIndex) {
        const markers = this.container.querySelectorAll('.scene-marker');
        markers.forEach((marker, index) => {
            marker.classList.toggle('active', index === activeIndex);
            marker.classList.toggle('visited', index < activeIndex);
            
            if (index === activeIndex) {
                marker.style.background = '#4CAF50';
            } else if (index < activeIndex) {
                marker.style.background = 'rgba(76, 175, 80, 0.5)';
            } else {
                marker.style.background = 'rgba(255,255,255,0.3)';
            }
        });
    }
    
    bindEvents() {
        // Click on scene markers
        this.container.addEventListener('click', (e) => {
            const marker = e.target.closest('.scene-marker');
            if (marker) {
                const index = parseInt(marker.dataset.index);
                this.goToScene(index);
            }
        });
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight') this.nextScene();
            if (e.key === 'ArrowLeft') this.prevScene();
        });
        
        // Click on the media to advance
        const media = this.container.querySelector('.scene-image, .media-player');
        if (media) {
            media.addEventListener('click', () => this.nextScene());
        }
    }
    
    goToScene(index) {
        if (index < 0) index = 0;
        if (index >= this.scenes.length) index = this.scenes.length - 1;
        this.updateScene(index);
    }
    
    nextScene() {
        this.goToScene(this.currentIndex + 1);
    }
    
    prevScene() {
        this.goToScene(this.currentIndex - 1);
    }
    
    play() {
        this.isPlaying = true;
        // Auto-advance every 3 seconds
        this.interval = setInterval(() => {
            if (this.currentIndex < this.scenes.length - 1) {
                this.nextScene();
            } else {
                this.stop();
            }
        }, 3000);
    }
    
    stop() {
        this.isPlaying = false;
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CiteCastPlayer;
}