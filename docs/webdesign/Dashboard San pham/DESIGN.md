---
name: Precision Analytics
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#0058be'
  on-secondary: '#ffffff'
  secondary-container: '#2170e4'
  on-secondary-container: '#fefcff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#002113'
  on-tertiary-container: '#009668'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  container-margin: 24px
  gutter: 16px
---

## Brand & Style

The design system is engineered for high-density data visualization and market analysis. It prioritizes **Modern Corporate** aesthetics, blending the rigor of financial terminals with the accessibility of contemporary SaaS. The visual language evokes a sense of "Computational Trust"—where every pixel serves the purpose of clarity and every layout choice facilitates rapid data scanning.

The system avoids decorative flourishes in favor of structural integrity. It utilizes a strict hierarchy, subtle depth through layering, and a disciplined color application to ensure that critical price fluctuations and market trends remain the focal point of the user experience.

## Colors

This design system utilizes a high-contrast palette designed for professional environments. 

- **Deep Navy (#0F172A):** Used for primary text, side navigation, and core structural elements to ground the UI in authority.
- **Tech Blue (#3B82F6):** The primary action color, used for interactive elements, primary buttons, and active state indicators.
- **Emerald Green (#10B981):** Specifically reserved for positive price delta indicators, "Buy" signals, and success states.
- **Semantic Red (#EF4444):** (Implicit) Used sparingly for price increases or critical alerts.
- **Surface Scale:** A refined range of slates (from #F8FAFC to #E2E8F0) provides the background for data cards and table rows, ensuring optimal legibility.

## Typography

The typography system is built on **Inter**, chosen for its exceptional legibility in data-heavy contexts. A secondary monospaced font is introduced for tabular price data to ensure numeric alignment.

- **Scale:** The system uses a condensed typographic scale to maximize information density without sacrificing readability.
- **Hierarchy:** Use `headline-md` for card titles and `label-md` (all-caps) for table headers.
- **Numerics:** All price points and technical specifications should use tabular lining figures to ensure that columns of data remain perfectly aligned for vertical scanning.

## Layout & Spacing

The layout follows a **12-column fluid grid** system optimized for widescreen dashboard consumption. 

- **Grid:** On desktop, use a 12-column grid with 16px gutters. For analytics widgets, standard widths are 3, 4, 6, or 12 columns.
- **Density:** Use a tight 4px baseline grid. Padding within data cards should be kept to a maximum of `lg` (24px) for primary containers and `md` (16px) for nested lists.
- **Breakpoints:**
  - **Desktop (1280px+):** Full side-navigation and multi-column widget layouts.
  - **Tablet (768px - 1279px):** Navigation collapses to icons; widgets reflow to 2-column stacks.
  - **Mobile (Under 768px):** Single column stack with 16px horizontal margins.

## Elevation & Depth

To maintain a "flat yet functional" look, depth is communicated through subtle tonal changes and hair-line borders rather than heavy shadows.

- **Surface Tiers:** The main background is the lowest tier (#F8FAFC). Data cards sit on the middle tier (#FFFFFF).
- **Outlines:** Use 1px solid borders (#E2E8F0) for all container elements. This provides "grid-like" precision.
- **Shadows:** Apply a singular, very soft ambient shadow for interactive cards (`0 1px 3px 0 rgba(0, 0, 0, 0.05)`).
- **Active States:** Elements being hovered or dragged should use a "Tech Blue" subtle outer glow or a 2px border to indicate focus without shifting the layout.

## Shapes

The shape language is conservative and professional. 

- **Corner Radius:** A standard 4px (`0.25rem`) radius is applied to buttons, input fields, and small UI components. 
- **Container Radius:** Larger data cards and dashboard modules may use up to 8px (`0.5rem`) for a slightly more modern feel, but no larger.
- **Interactive Elements:** Checkboxes and radio buttons maintain sharp, precise corners (2px radius) to align with the technical nature of price tracking.

## Components

### Buttons
- **Primary:** Deep Navy background with White text. High-contrast and authoritative.
- **Secondary:** White background, 1px border (#E2E8F0), Tech Blue text.
- **Ghost:** No background, Tech Blue text. Used for "Add Filter" or "Export" actions.

### Data Cards
Every card must have a 1px border and a subtle white-to-gray vertical gradient or solid white background. Headers should be separated by a light horizontal rule.

### Input Fields
Strict rectangular forms with 1px borders. Use a focus state of Tech Blue with a 1px inset shadow to emphasize precision.

### Chips & Indicators
- **Price Up:** Emerald Green background (10% opacity) with Emerald Green text and a small upward chevron.
- **Price Down:** Semantic Red background (10% opacity) with Red text and a small downward chevron.

### List Items
Table rows should have a hover state of #F1F5F9. Use "Inter" for text and "JetBrains Mono" for all price/currency values.

### Additional Components
- **Trend Sparklines:** Simplified line charts without axes, used within table rows to show 7-day price history.
- **Global Search:** A prominent, wide input at the top of the dashboard for specific laptop models/SKUs.