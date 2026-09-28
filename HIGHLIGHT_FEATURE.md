# Highlight-to-Ask Feature Documentation

## Overview
The Highlight-to-Ask feature allows users to highlight any portion of Bible verses and ask the AI for deeper biblical interpretation - all while maintaining the app's core philosophy of self-referential biblical interpretation (the Bible explains itself).

## How It Works

### User Experience Flow
1. **Select Text**: User highlights any portion of a verse they're reading
2. **Tooltip Appears**: A modern, floating "Ask" button appears above the selection
3. **Click to Ask**: User clicks the "Ask" button
4. **AI Responds**: The AI generates commentary explaining the highlighted portion using other Bible verses

### Features

#### 1. Smart Context Detection
- Automatically detects when text is selected within verse content
- Captures verse reference (Book, Chapter, Verse) when available
- Builds contextual queries that include the source reference

#### 2. Modern UI/UX
- **Smooth animations**: Tooltip fades in with subtle transform
- **Smart positioning**: Always appears above selected text, repositions if near screen edges
- **Visual feedback**: Custom selection highlight color (teal/green)
- **Responsive**: Works on both mouse and touch devices
- **Accessible**: Proper ARIA labels and keyboard support

#### 3. Context-Aware Queries
The AI receives different query formats based on available context:

**With Full Reference:**
```
"What does the Bible mean when it says '[highlighted text]' in [Book Chapter:Verse]? 
Please explain using other Bible verses."
```

**With Full Verse Text:**
```
"What does the Bible mean when it says '[highlighted text]'? 
The full verse is: '[full verse]'. Please explain using other Bible verses."
```

**Highlighted Text Only:**
```
"What does the Bible mean when it says '[highlighted text]'? 
Please explain this using other Bible verses and biblical context."
```

### Implementation Details

#### Files Modified/Created

1. **frontend/index.html**
   - Added tooltip HTML element with "Ask" button
   - Added highlight.js script reference

2. **frontend/style.css**
   - Tooltip styling with modern gradient button
   - Smooth animations and transitions
   - Custom selection highlight color
   - Responsive positioning

3. **frontend/highlight.js** (NEW)
   - HighlightManager class
   - Text selection detection
   - Tooltip positioning logic
   - Context extraction from verse elements
   - Integration with commentary system

#### Key Components

**HighlightManager Class:**
- `init()`: Sets up event listeners
- `handleSelection()`: Detects and validates text selection
- `isSelectionInVerse()`: Checks if selection is within verse content
- `getSelectionContext()`: Extracts verse reference and context
- `showTooltip()`: Displays and positions the tooltip
- `handleAskClick()`: Builds query and triggers AI commentary
- `buildContextualQuery()`: Creates context-aware queries for AI

### Design Philosophy

The feature maintains the app's core philosophy:
- **Self-Referential**: All AI responses explain Bible using Bible
- **Context-Aware**: Includes verse references when available
- **User-Centric**: Simple, intuitive interaction
- **Modern**: Clean, minimal design inspired by modern chat interfaces

### CSS Styling

```css
.tooltip-button {
  /* Modern gradient button */
  background: linear-gradient(135deg, #10a37f, #0d8a6a);
  
  /* Smooth hover effects */
  box-shadow: 0 4px 12px rgba(16, 163, 127, 0.3);
  
  /* Rounded pill shape */
  border-radius: 9999px;
}

/* Custom selection color */
::selection {
  background-color: rgba(16, 163, 127, 0.25);
}
```

### Event Handling

1. **mouseup/touchend**: Detects selection completion
2. **selectionchange**: Updates selected text (keyboard selection)
3. **scroll**: Repositions tooltip during scrolling
4. **mousedown**: Hides tooltip when clicking outside

### Integration with Commentary System

When user clicks "Ask":
1. Builds contextual query from highlighted text + context
2. Calls `commentaryManager.generateCommentary(query, 10)`
3. Scrolls to commentary section to show results
4. Clears selection and hides tooltip

### Logging & Analytics

The feature logs user interactions:
- `text_highlighted`: When user selects text
- `highlight_ask_clicked`: When user clicks "Ask" button

Logged data includes:
- Highlighted text (truncated to 100 chars)
- Text length
- Whether context was available

### Browser Compatibility

- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest versions)
- **Selection API**: Uses standard window.getSelection()
- **Touch Support**: touchend event for mobile devices
- **Fallback**: Gracefully degrades if tooltip elements not found

### Future Enhancements

Potential improvements:
- Remember user's highlighted sections
- Share highlighted portions with questions
- Multi-highlight support (highlight multiple passages)
- Highlight persistence across sessions
- Export highlights with AI explanations

## Usage Examples

### Example 1: From Search Results
1. Search for "faith without works"
2. Select "faith without works is dead"
3. Click "Ask"
4. AI explains using James 2:26 and related verses

### Example 2: From Chapter View
1. Open 2 Timothy 4
2. Highlight "make full proof of thy ministry" (verse 5)
3. Click "Ask"
4. AI provides biblical context from other passages

### Example 3: Specific Phrase
1. Reading Romans 8
2. Highlight "more than conquerors"
3. Click "Ask"
4. AI explains the phrase using biblical cross-references

## Technical Notes

### Minimum Selection Length
- Requires at least 3 characters to show tooltip
- Prevents accidental triggers on single characters

### Positioning Algorithm
```javascript
// Center above selection
left = selectionRect.left + (width / 2) - (tooltipWidth / 2)
top = selectionRect.top - tooltipHeight - 12px

// Keep within viewport (16px padding)
// Falls below selection if near top of screen
```

### Performance
- Debounced selection change handler (100ms)
- Efficient DOM queries using closest()
- Minimal reflows with transform animations

## Conclusion

The Highlight-to-Ask feature provides an intuitive, modern way for users to deepen their Bible study by asking questions about specific portions of scripture. It seamlessly integrates with the existing commentary system while maintaining the app's philosophy of self-referential biblical interpretation.
