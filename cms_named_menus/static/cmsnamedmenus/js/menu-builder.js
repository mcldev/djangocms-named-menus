/**
 * Modern Menu Builder
 * Vanilla JS implementation replacing jQuery Nestable
 * Features: Drag-and-drop, filtering, collapsible trees, optional child selection
 */

class MenuBuilder {
  constructor(options = {}) {
    this.availablePages = options.availablePages || [];
    this.selectedContainer = options.selectedContainer;
    this.availableContainer = options.availableContainer;
    this.hiddenField = options.hiddenField;
    this.includeChildrenCheckbox = options.includeChildrenCheckbox;

    this.sortableInstances = [];
    this.expandedStates = new Map();

    this.init();
  }

  init() {
    this.setupFilters();
    this.setupPanelControls();
    this.setupSortable();
    this.serializeMenu();

    // Save initial state on page load
    window.addEventListener('load', () => {
      this.serializeMenu();
    });
  }

  /**
   * Setup search/filter functionality for both panels
   */
  setupFilters() {
    const filters = document.querySelectorAll('.menu-filter');

    filters.forEach(filter => {
      const input = filter.querySelector('input');
      const clearBtn = filter.querySelector('.menu-filter-clear');
      const panel = filter.closest('.menu-panel');

      input.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();

        if (searchTerm) {
          filter.classList.add('has-value');
        } else {
          filter.classList.remove('has-value');
        }

        this.filterTree(panel, searchTerm);
      });

      clearBtn.addEventListener('click', () => {
        input.value = '';
        filter.classList.remove('has-value');
        this.filterTree(panel, '');
        input.focus();
      });
    });
  }

  /**
   * Filter tree items based on search term
   */
  filterTree(panel, searchTerm) {
    const items = panel.querySelectorAll('.menu-item');

    if (!searchTerm) {
      // Show all items
      items.forEach(item => {
        item.classList.remove('filtered-hidden');
        const title = item.querySelector('.menu-item-title');
        if (title) {
          // Remove highlighting
          title.innerHTML = title.textContent;
        }
      });
      return;
    }

    // First pass: mark matching items and highlight
    items.forEach(item => {
      const titleEl = item.querySelector('.menu-item-title');
      const title = titleEl.textContent.toLowerCase();

      if (title.includes(searchTerm)) {
        item.classList.remove('filtered-hidden');
        item.dataset.matches = 'true';

        // Highlight matching text
        const regex = new RegExp(`(${this.escapeRegex(searchTerm)})`, 'gi');
        titleEl.innerHTML = titleEl.textContent.replace(regex, '<mark>$1</mark>');
      } else {
        item.dataset.matches = 'false';
        titleEl.innerHTML = titleEl.textContent;
      }
    });

    // Second pass: show parents of matching items
    items.forEach(item => {
      if (item.dataset.matches === 'true') {
        this.showParentChain(item);
      } else if (!this.hasMatchingDescendant(item)) {
        item.classList.add('filtered-hidden');
      } else {
        item.classList.remove('filtered-hidden');
      }
    });
  }

  /**
   * Show all parent items up to root
   */
  showParentChain(item) {
    let parent = item.parentElement;
    while (parent) {
      if (parent.classList.contains('menu-item')) {
        parent.classList.remove('filtered-hidden');
        // Expand parent to show matched child
        parent.classList.remove('collapsed');
      }
      parent = parent.parentElement;
    }
  }

  /**
   * Check if item has any matching descendants
   */
  hasMatchingDescendant(item) {
    const descendants = item.querySelectorAll('.menu-item');
    return Array.from(descendants).some(desc => desc.dataset.matches === 'true');
  }

  /**
   * Escape special regex characters
   */
  escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  /**
   * Setup expand/collapse controls for panels
   */
  setupPanelControls() {
    const expandAllBtns = document.querySelectorAll('[data-action="expand-all"]');
    const collapseAllBtns = document.querySelectorAll('[data-action="collapse-all"]');

    expandAllBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const panel = e.target.closest('.menu-panel');
        this.expandAll(panel);
      });
    });

    collapseAllBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const panel = e.target.closest('.menu-panel');
        this.collapseAll(panel);
      });
    });

    // Setup individual item toggles
    this.setupItemToggles();
  }

  /**
   * Setup toggle buttons for individual items
   */
  setupItemToggles() {
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('menu-item-toggle')) {
        const item = e.target.closest('.menu-item');
        this.toggleItem(item);
      }
    });
  }

  /**
   * Toggle item expand/collapse
   */
  toggleItem(item) {
    const toggle = item.querySelector('.menu-item-toggle');
    const isCollapsed = item.classList.toggle('collapsed');

    if (isCollapsed) {
      toggle.classList.remove('expanded');
      toggle.classList.add('collapsed');
    } else {
      toggle.classList.remove('collapsed');
      toggle.classList.add('expanded');
    }

    // Remember state
    const itemId = item.dataset.id;
    if (itemId) {
      this.expandedStates.set(itemId, !isCollapsed);
    }
  }

  /**
   * Expand all items in a panel
   */
  expandAll(panel) {
    const items = panel.querySelectorAll('.menu-item');
    items.forEach(item => {
      item.classList.remove('collapsed');
      const toggle = item.querySelector('.menu-item-toggle');
      if (toggle) {
        toggle.classList.remove('collapsed');
        toggle.classList.add('expanded');
      }
    });
  }

  /**
   * Collapse all items in a panel
   */
  collapseAll(panel) {
    const items = panel.querySelectorAll('.menu-item');
    items.forEach(item => {
      if (!item.classList.contains('no-children')) {
        item.classList.add('collapsed');
        const toggle = item.querySelector('.menu-item-toggle');
        if (toggle) {
          toggle.classList.remove('expanded');
          toggle.classList.add('collapsed');
        }
      }
    });
  }

  /**
   * Setup SortableJS for drag-and-drop functionality
   */
  setupSortable() {
    const baseOptions = {
      animation: 150,
      fallbackOnBody: true,
      swapThreshold: 0.65,
      group: 'shared',
      handle: '.menu-item-handle',
      ghostClass: 'ghost',
      chosenClass: 'chosen',
      dragClass: 'dragging',

      onEnd: (evt) => {
        this.handleDragEnd(evt);
        // Re-initialize sortable on any new nested lists
        this.initializeNestedSortables();
      },

      onStart: (evt) => {
        this.handleDragStart(evt);
      }
    };

    // Initialize sortable for selected menu
    const selectedLists = this.selectedContainer.querySelectorAll('.menu-tree');
    selectedLists.forEach(list => {
      if (!list.sortableInstance) {
        list.sortableInstance = new Sortable(list, {
          ...baseOptions,
          onAdd: (evt) => this.serializeMenu()
        });
        this.sortableInstances.push(list.sortableInstance);
      }
    });

    // Initialize sortable for available pages
    const availableLists = this.availableContainer.querySelectorAll('.menu-tree');
    availableLists.forEach(list => {
      if (!list.sortableInstance) {
        list.sortableInstance = new Sortable(list, {
          ...baseOptions,
          onRemove: (evt) => {
            // Rebuild available pages to original state
            this.rebuildAvailablePages();
          }
        });
        this.sortableInstances.push(list.sortableInstance);
      }
    });
  }

  /**
   * Initialize sortable on any new nested lists (for unlimited nesting depth)
   */
  initializeNestedSortables() {
    // Find all menu-tree elements in selected container
    const allLists = this.selectedContainer.querySelectorAll('.menu-tree');

    allLists.forEach(list => {
      // Only initialize if not already initialized
      if (!list.sortableInstance) {
        list.sortableInstance = new Sortable(list, {
          animation: 150,
          fallbackOnBody: true,
          swapThreshold: 0.65,
          group: 'shared',
          handle: '.menu-item-handle',
          ghostClass: 'ghost',
          chosenClass: 'chosen',
          dragClass: 'dragging',

          onEnd: (evt) => {
            this.handleDragEnd(evt);
            this.initializeNestedSortables();
          },

          onStart: (evt) => {
            this.handleDragStart(evt);
          },

          onAdd: (evt) => {
            this.serializeMenu();
          }
        });

        this.sortableInstances.push(list.sortableInstance);
      }
    });
  }

  /**
   * Handle drag start event
   */
  handleDragStart(evt) {
    const item = evt.item;
    const checkbox = item.querySelector('input[type="checkbox"][data-include-children]');
    const includeChildren = checkbox ? checkbox.checked : this.includeChildrenCheckbox?.checked;

    // If not including children, remove child elements during drag
    if (!includeChildren) {
      const childTree = item.querySelector('.menu-tree');
      if (childTree) {
        // Store children temporarily
        item.dataset.tempChildren = childTree.outerHTML;
        childTree.remove();
      }
    }
  }

  /**
   * Handle drag end event
   */
  handleDragEnd(evt) {
    const item = evt.item;

    // Restore children if they were removed
    if (item.dataset.tempChildren) {
      const childTree = document.createElement('div');
      childTree.innerHTML = item.dataset.tempChildren;
      item.appendChild(childTree.firstChild);
      delete item.dataset.tempChildren;
    }

    // Update serial representation
    this.serializeMenu();
  }

  /**
   * Rebuild available pages list to original state
   */
  rebuildAvailablePages() {
    const container = this.availableContainer.querySelector('.menu-tree');
    if (!container) return;

    // Clear and rebuild from original data
    container.innerHTML = '';
    this.renderTree(this.availablePages, container);

    // Re-initialize sortable
    this.sortableInstances = this.sortableInstances.filter(instance => {
      if (instance.el.closest('.available-pages')) {
        delete instance.el.sortableInstance;
        instance.destroy();
        return false;
      }
      return true;
    });

    const availableLists = this.availableContainer.querySelectorAll('.menu-tree');
    availableLists.forEach(list => {
      if (!list.sortableInstance) {
        list.sortableInstance = new Sortable(list, {
          ...this.getSortableOptions(),
          onRemove: () => this.rebuildAvailablePages()
        });
        this.sortableInstances.push(list.sortableInstance);
      }
    });
  }

  /**
   * Get sortable options
   */
  getSortableOptions() {
    return {
      animation: 150,
      fallbackOnBody: true,
      swapThreshold: 0.65,
      group: 'shared',
      handle: '.menu-item-handle',
      ghostClass: 'ghost',
      chosenClass: 'chosen',
      dragClass: 'dragging',
      onEnd: (evt) => this.handleDragEnd(evt),
      onStart: (evt) => this.handleDragStart(evt)
    };
  }

  /**
   * Render tree from data
   */
  renderTree(nodes, container) {
    nodes.forEach(node => {
      const item = this.createMenuItem(node);
      container.appendChild(item);
    });
  }

  /**
   * Create menu item element
   */
  createMenuItem(node) {
    const li = document.createElement('li');
    li.className = 'menu-item';
    li.dataset.id = node.id;
    li.dataset.title = node.title;

    if (!node.children || node.children.length === 0) {
      li.classList.add('no-children');
    }

    const content = document.createElement('div');
    content.className = 'menu-item-content';

    // Drag handle
    const handle = document.createElement('div');
    handle.className = 'menu-item-handle';
    content.appendChild(handle);

    // Toggle button (for items with children)
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'menu-item-toggle expanded';
    content.appendChild(toggle);

    // Title
    const title = document.createElement('div');
    title.className = 'menu-item-title';
    title.textContent = node.title || node.content || '';
    content.appendChild(title);

    li.appendChild(content);

    // Render children recursively
    if (node.children && node.children.length > 0) {
      const childTree = document.createElement('ol');
      childTree.className = 'menu-tree';
      this.renderTree(node.children, childTree);
      li.appendChild(childTree);
    }

    return li;
  }

  /**
   * Serialize menu tree to JSON
   */
  serializeMenu() {
    const tree = this.selectedContainer.querySelector('.menu-tree');
    const data = this.serializeTree(tree);

    if (this.hiddenField) {
      this.hiddenField.value = JSON.stringify(data);
    }

    this.selectedContainer.classList.toggle('has-items', data.length > 0);

    return data;
  }

  /**
   * Serialize tree element to nested array
   */
  serializeTree(container) {
    if (!container) return [];

    const items = Array.from(container.children).filter(el => el.classList.contains('menu-item'));

    return items.map(item => {
      const data = {
        id: parseInt(item.dataset.id),
        title: item.dataset.title
      };

      const childTree = item.querySelector(':scope > .menu-tree');
      if (childTree) {
        const children = this.serializeTree(childTree);
        if (children.length > 0) {
          data.children = children;
        }
      }

      return data;
    });
  }

  /**
   * Count total descendants
   */
  countDescendants(item) {
    let count = 0;
    const childItems = item.querySelectorAll('.menu-item');
    return childItems.length;
  }
}

/**
 * Initialize menu builder when DOM is ready
 */
document.addEventListener('DOMContentLoaded', () => {
  const selectedContainer = document.querySelector('.menu-pages');
  const availableContainer = document.querySelector('.available-pages');
  const hiddenField = document.getElementById('id_pages');
  const includeChildrenCheckbox = document.getElementById('include_child_items');

  if (selectedContainer && availableContainer && hiddenField) {
    window.menuBuilder = new MenuBuilder({
      availablePages: window.availablePagesData || [],
      selectedContainer,
      availableContainer,
      hiddenField,
      includeChildrenCheckbox
    });
  }
});
