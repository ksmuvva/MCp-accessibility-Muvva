# 🧠 Sequential Thinking Commands for Accessibility MCP

The Sequential Thinking MCP server adds structured problem-solving to your accessibility workflows. This guide provides practical commands and usage examples.

## 🔍 Basic Sequential Thinking Commands

### Problem Analysis
```
"Think through this accessibility issue step by step: why does color contrast fail on navigation elements but not body text?"
```

### Planning & Strategy  
```
"Plan a comprehensive approach to fix all WCAG 2.2 AA violations on this page, considering the priority and dependencies between issues"
```

### Root Cause Analysis
```
"Analyze step by step: why do these accessibility violations only appear in the production environment but not in staging?"
```

### Decision Making
```
"Think through the pros and cons of using aria-label versus fixing the actual markup structure for this form field"
```

## 🎯 Combined Accessibility + Sequential Thinking Commands

### Audit + Analysis Workflow
```
"First audit https://example.com for accessibility issues, then think through the findings to categorize them by severity and complexity"
```

### Remediation Planning
```
"Audit the homepage for accessibility, then systematically think through a remediation strategy starting with critical issues"
```

### Complex Investigation
```
"Audit this multi-page form flow, then think through each step to identify where keyboard navigation breaks down"
```

### Compliance Strategy
```
"Review our entire site's accessibility status, then think through what we need to fix to achieve WCAG 2.2 AA compliance step by step"
```

## 📋 Domain-Specific Sequential Thinking

### Skip Links
```
"Think through the best approach to implement skip navigation that works across all our different page layouts"
```

### Color Contrast  
```
"Analyze our color palette step by step: determine which contrast failures should be fixed with color changes versus structural changes"
```

### Forms
```
"Break down this complex multi-step form's accessibility issues: identify which fields are problematic, why they fail, and how to fix them systematically"
```

### Dynamic Content
```
"Think through how to make our dynamic content more accessible: consider ARIA regions, live regions, and screen reader announcements step by step"
```

### Mobile Accessibility
```
"Analyze our responsive design: think through how the layout changes affect accessibility at different breakpoints and where the failures occur"
```

## 🛠️ Technical Problem Solving

### Browser Testing Strategy
```
"Plan a systematic approach to test our site across different browsers: prioritize by user base, common issues, and testing efficiency"
```

### Performance vs Accessibility Trade-offs  
```
"Think through the trade-offs between loading additional JavaScript for accessibility features versus page performance"
```

### Third-Party Component Analysis
```
"Step by step, analyze which third-party components cause accessibility issues and what alternatives exist for each"
```

### Accessibility Statement Planning
```
"Think through how to write an accessibility statement that accurately represents our current compliance status while being honest about limitations"
```

## 🎓 Learning & Documentation

### Understanding Complex Rules
```
"Help me understand the difference between WCAG 2.1 and WCAG 2.2 criteria for color contrast, and which applies to our site"
```

### Training Development
```
"Plan an accessibility training program for our development team, structured by topic and role"
```

### Documentation Strategy  
```
"Think through how to document our accessibility decisions so future developers understand the reasoning"
```

## 🔧 Integration Examples

### With Audit Data
```
"Audit the checkout flow, then think through how to prioritize fixing the 12 violations found based on business impact and technical complexity"
```

### With Site Scanning  
```
"Scan our entire site, then systematically plan which accessibility improvements to tackle first this quarter"
```

### With Interactive Testing
```
"Use browser navigation to test our logged-in experience, then think through how the accessibility differs from the logged-out state"
```

## 💡 Advanced Usage

### Branching Alternatives
```
"Consider two different approaches to fixing this keyboard navigation issue, and think through which is better for maintainability"
```

### Hypothesis Verification  
```
"I have a theory about why this aria-label is being ignored by screen readers. Test this hypothesis step by step and revise your thinking based on results"
```

### Retrospective Analysis  
```
"Think through why we missed these accessibility issues during development, and plan how to improve our process for next time"
```

## 🚀 Quick Start Examples

**Basic:**
```
"Think through how to fix this alt text issue"
```

**Advanced:**  
```
"Audit the site, then think through a comprehensive accessibility improvement plan for Q4"
```

**Expert:**
```
"Analyze the interaction between our accessibility issues and performance optimizations, considering both user experience and technical constraints"
```

## 🎯 How Sequential Thinking Works

The `sequential_thinking` tool accepts these parameters:
- **thought**: Current thinking step
- **thoughtNumber**: Current step number  
- **totalThoughts**: Estimated total steps
- **nextThoughtNeeded**: Whether more thinking is required
- **isRevision**: Whether this revises previous thinking
- **branchFromThought**: Alternative reasoning paths
- **branchId**: Branch identifier for alternative approaches

Claude will automatically manage these parameters when you use natural sequential thinking requests.

## 💡 Pro Tips

1. **Be Specific**: Clear problem statements lead to better sequential thinking
2. **Use Context**: Reference specific audit results when available  
3. **Iterate**: Ask for revisions if the first approach needs refinement
4. **Combine Tools**: Use with browser_* tools for interactive testing
5. **Think Aloud**: Claude will show its reasoning process step by step

## 🎓 Example Workflows

### **Full Accessibility Audit Cycle**
```
1. audit_site("https://example.com", max_pages=10)
2. "Think through the results and prioritize the most critical issues"
3. "Plan remediation for the top 5 accessibility violations"
4. "Consider the technical constraints and business requirements"
5. "Branch if needed: what if client requires a different approach?"
```

### **Root Cause Investigation**
```
1. audit_current_page(session_id)  // Test logged-in state
2. "Think through why this issue only occurs when logged in"
3. "Consider authentication flow, dynamic content, permissions"
4. "Form hypothesis and revise thinking based on findings"
```

### **Strategic Planning**
```
1. list_wcag_rules()  // See all criteria
2. "Think through which criteria our site currently fails"
3. "Plan a roadmap to achieve WCAG 2.2 AA compliance"
4. "Consider resource requirements and timeline"
5. "Adjust plan based on feasibility and priority"
```