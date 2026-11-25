/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.CarSelectionWidget = publicWidget.Widget.extend({
    selector: "#create-maintenance-modal",

    events: {
        'change #property-images': '_onImageChange',
        'click .remove-image': '_onRemoveImage',
        'submit': '_onSubmit',
    },
    
    /**
     * Initialize the widget
     */
    async start() {
        this.uploadedImages = [];
        this.submitButton = this.$el.find("button[type='submit']")[0];
    },
    
    /**
     * Handle image selection
     */
    _onImageChange: function(ev) {
        const files = Array.from(ev.target.files);
        const previewContainer = this.$el.find("#image-preview")[0];
        previewContainer.innerHTML = '';
        files.forEach((file, index) => {
            if (!file.type.match('image.*')) return;
            
            const reader = new FileReader();
            reader.onload = (e) => {
                const previewDiv = document.createElement('div');
                previewDiv.className = 'image-thumbnail-container mr-2 mb-2';
                previewDiv.innerHTML = `
                    <div class="image-thumbnail" style="background-image: url(${e.target.result})"></div>
                    <button type="button" class="btn btn-danger btn-sm remove-image" data-index="${index}">
                        <i class="fa fa-times"></i>
                    </button>
                `;
                previewContainer.appendChild(previewDiv);
            };
            reader.readAsDataURL(file);
        });
        this.uploadedImages = files;
    },
    
    /**
     * Handle image removal
     */
    _onRemoveImage: function(ev) {
        const index = parseInt(ev.currentTarget.dataset.index, 10);
        this.uploadedImages.splice(index, 1);
        
        // Update preview
        const previewContainer = this.$el.find("#image-preview")[0];
        previewContainer.innerHTML = '';
        
        this.uploadedImages.forEach((file, idx) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const previewDiv = document.createElement('div');
                previewDiv.className = 'image-thumbnail-container mr-2 mb-2';
                previewDiv.innerHTML = `
                    <div class="image-thumbnail" style="background-image: url(${e.target.result})"></div>
                    <button type="button" class="btn btn-danger btn-sm remove-image" data-index="${idx}">
                        <i class="fa fa-times"></i>
                    </button>
                `;
                previewContainer.appendChild(previewDiv);
            };
            reader.readAsDataURL(file);
        });
        
        // Update file input
        const dataTransfer = new DataTransfer();
        this.uploadedImages.forEach(file => dataTransfer.items.add(file));
        this.$('#property-images')[0].files = dataTransfer.files;
    },
    
    async _onSubmit(ev) {
        ev.preventDefault();
        this.submitButton.disabled = true;
        this.submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Processing...';
        
        const formData = new FormData(ev.target);
        
        // Add images to form data
        this.uploadedImages.forEach((file, index) => {
            formData.append('attachments', file);  // Use same name for all images
        });


        // Submit via fetch API to properly handle file uploads
        const response = await fetch('/maintenance/create', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRF-TOKEN': formData.get('csrf_token'),
            },
        });
        this.uploadedImages = [];
        window.location.href = `/my/maintenance`;

    }
})
