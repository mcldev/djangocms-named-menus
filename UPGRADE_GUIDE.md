# Menu Builder Modernization - Upgrade Guide

## Overview

The Django CMS Named Menus admin interface has been modernized with:
- **Vanilla JavaScript** (replacing jQuery Nestable from 2018)
- **SortableJS** - modern, lightweight drag-and-drop library (45KB vs 400KB+ jQuery stack)
- **Modern CSS Grid/Flexbox** layout
- **Enhanced features**: filtering, collapsible trees, better UX

## What Changed

### ✅ Removed Dependencies
- ❌ jQuery 3.3.1 (85KB, 2018)
- ❌ jQuery UI (248KB, 2018)
- ❌ jQuery Nestable (57KB, 2018)
- **Total removed: ~400KB of legacy JavaScript**

### ✅ Added Dependencies
- ✅ SortableJS 1.15.2 (45KB, actively maintained)
- ✅ Modern vanilla JavaScript (~10KB)
- **Total added: ~55KB**

### ✅ New Features

#### 1. **Real-time Filtering/Search**
- Search box in both "Selected Pages" and "Available Pages" panels
- Type to filter pages by title
- Automatically shows parent items of matching children
- Highlights matched text
- Clear button to reset filter

#### 2. **Collapsible Tree Management**
- **Expand All / Collapse All** buttons for each panel
- Individual expand/collapse controls per item
- Remembers expanded state during session
- Smooth animations

#### 3. **Enhanced Drag & Drop**
- Visual feedback with ghost preview
- Smoother animations (150ms transitions)
- Better touch support for tablets
- Accessible with keyboard navigation

#### 4. **Improved UI/UX**
- Modern card-based panels with shadows
- Color-coded drag handles
- Hover states and visual feedback
- Children count badges
- Responsive design (works on mobile/tablet)
- Better accessibility (ARIA labels, focus states)

#### 5. **Optional Child Selection** (Enhanced)
- "Include Child Items" checkbox (preserved from old version)
- Now works more reliably with modern drag system
- Visual indication of how many children will be included

## Files Changed

### New Files
```
cms_named_menus/static/cmsnamedmenus/
├── css/menu-builder.css         # Modern styles with CSS Grid
├── js/menu-builder.js           # Vanilla JS implementation
└── js/sortable.min.js           # SortableJS library

cms_named_menus/templates/cms_named_menus/
└── menu_item.html               # New menu item template
```

### Modified Files
```
cms_named_menus/templates/cms_named_menus/
└── admin_select.html            # Updated to use new components
```

### Backup Files (for rollback)
```
cms_named_menus/templates/cms_named_menus/
├── admin_select_old.html        # Original template
└── nestable_item.html           # Original item template
```

### Deprecated Files (can be removed after testing)
```
cms_named_menus/static/cmsnamedmenus/ext/
├── jquery-3.3.1.min.js          # jQuery (no longer needed)
├── jquery-ui.min.js             # jQuery UI (no longer needed)
├── jquery.nestable.js           # jQuery Nestable (no longer needed)
├── jquery.nestable.min.js       # jQuery Nestable minified
└── jquery.nestable.min.css      # jQuery Nestable styles
```

## Testing Checklist

After upgrading, test the following functionality:

### Basic Functionality
- [ ] Admin page loads without JavaScript errors
- [ ] Both panels display correctly
- [ ] Drag items from Available → Selected
- [ ] Drag items within Selected panel to reorder
- [ ] Nested items can be reordered
- [ ] Hidden field is updated with JSON on changes
- [ ] Form saves correctly
- [ ] Menu displays correctly on frontend

### New Features
- [ ] Filter box works in Selected panel
- [ ] Filter box works in Available panel
- [ ] Matching items are highlighted
- [ ] Parent items show when children match
- [ ] Clear filter button works
- [ ] Expand All button works
- [ ] Collapse All button works
- [ ] Individual expand/collapse toggles work
- [ ] "Include Child Items" checkbox works
- [ ] Children count badges display correctly

### Edge Cases
- [ ] Empty menu (no selected pages)
- [ ] Menu with deeply nested items (5+ levels)
- [ ] Very long page titles
- [ ] Special characters in page titles
- [ ] Filtering with no matches
- [ ] Dragging parent without children
- [ ] Dragging parent with children (both modes)

### Browser Compatibility
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

### Accessibility
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
- [ ] Focus states visible
- [ ] ARIA labels present

## Rollback Instructions

If you need to rollback to the old jQuery-based version:

```bash
# Restore old template
cp cms_named_menus/templates/cms_named_menus/admin_select_old.html \
   cms_named_menus/templates/cms_named_menus/admin_select.html

# Or manually update admin_select.html to use old CSS/JS:
# - Link to jquery.nestable.min.css
# - Include jquery-3.3.1.min.js
# - Include jquery-ui.min.js
# - Include jquery.nestable.min.js
# - Use old inline script from admin_select_old.html
```

## Performance Improvements

### Load Time
- **Before**: ~400KB JavaScript + CSS
- **After**: ~55KB JavaScript + CSS
- **Improvement**: ~86% reduction in asset size

### Runtime Performance
- Modern vanilla JS is faster than jQuery
- SortableJS uses efficient DOM operations
- CSS transitions are GPU-accelerated
- No jQuery overhead for every operation

## Migration for Custom Modifications

If you've customized the old menu builder:

### Custom CSS
Old classes still exist for compatibility:
- `.pages` → `.menu-builder-container`
- `.dd` → `.menu-panel-body`
- `.dd-list` → `.menu-tree`
- `.dd-item` → `.menu-item`
- `.dd-handle` → `.menu-item-handle`

### Custom JavaScript
Replace jQuery calls:
- `$('.menu-pages.dd').nestable()` → Uses `MenuBuilder` class
- `$('.menu-pages.dd').nestable('serialize')` → `menuBuilder.serializeMenu()`
- Access via: `window.menuBuilder`

## Browser Support

### Minimum Supported Versions
- Chrome/Edge: 88+ (2021)
- Firefox: 85+ (2021)
- Safari: 14+ (2020)
- iOS Safari: 14+ (2020)
- Chrome Android: 88+ (2021)

### Required Features
- ES6+ JavaScript (classes, arrow functions, template literals)
- CSS Grid
- CSS Custom Properties (variables)
- Flexbox

## Future Enhancements

Potential features to add:

1. **Bulk Operations**
   - Select multiple items
   - Delete selected items
   - Move selected items

2. **Advanced Filtering**
   - Filter by page type
   - Filter by publish status
   - Sort options (alphabetical, date, custom)

3. **Keyboard Shortcuts**
   - Ctrl+F: Focus filter
   - Ctrl+E: Expand all
   - Ctrl+C: Collapse all

4. **Undo/Redo**
   - History stack for changes
   - Ctrl+Z / Ctrl+Y support

5. **Drag Improvements**
   - Multi-select drag
   - Copy mode (Ctrl+drag)
   - Restrict nesting depth

6. **Export/Import**
   - Export menu structure as JSON
   - Import from JSON
   - Duplicate menus

## Support

For issues or questions:
- Check browser console for JavaScript errors
- Verify all static files are served correctly
- Check Django admin media is configured
- Review this upgrade guide

## Changelog

### v2.0.0 (Modern Menu Builder)
- ✅ Replaced jQuery/Nestable with SortableJS
- ✅ Added real-time filtering/search
- ✅ Added collapsible tree controls
- ✅ Modern CSS Grid layout
- ✅ Improved accessibility
- ✅ Better mobile support
- ✅ 86% reduction in JavaScript size
- ✅ Smoother animations
- ✅ Better visual design
