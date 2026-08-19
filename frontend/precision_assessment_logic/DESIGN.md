---
name: Precision Assessment Logic
colors:
  surface: '#faf8ff'
  surface-dim: '#d9d9e5'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3fe'
  surface-container: '#ededf9'
  surface-container-high: '#e7e7f3'
  surface-container-highest: '#e1e2ed'
  on-surface: '#191b23'
  on-surface-variant: '#434655'
  inverse-surface: '#2e3039'
  inverse-on-surface: '#f0f0fb'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#585f6c'
  on-secondary: '#ffffff'
  secondary-container: '#dce2f3'
  on-secondary-container: '#5e6572'
  tertiary: '#943700'
  on-tertiary: '#ffffff'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#dce2f3'
  secondary-fixed-dim: '#c0c7d6'
  on-secondary-fixed: '#151c27'
  on-secondary-fixed-variant: '#404754'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#faf8ff'
  on-background: '#191b23'
  surface-variant: '#e1e2ed'
typography:
  display-lg:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-desktop: 64px
  margin-mobile: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is engineered for a high-stakes AI utility environment where clarity and trust are paramount. The brand personality is **analytical, transparent, and efficient**, designed to reassure users—ranging from insurance adjusters to vehicle owners—that the AI's diagnostic capabilities are backed by rigorous logic.

The design style follows a **Modern Corporate Minimalism** approach. It leverages generous whitespace and a "Functional White" aesthetic to reduce cognitive load during complex data entry and photo review tasks. The UI feels polished and lightweight, utilizing subtle depth and high-quality typography to establish a professional hierarchy. Visual tension is kept low to ensure the focus remains entirely on the vehicle assessment data and high-resolution imagery.

## Colors

The palette is anchored by **Precision Blue (#2563EB)**, used strategically for primary actions and progress indicators to signal intelligence and reliability. The foundation is built on a "Soft-Neutral" scale:

- **Primary:** Used for the "North Star" actions (e.g., "Submit Assessment", "Analyze Photo").
- **Surface & Background:** A clear distinction between the canvas (#F9FAFB) and active modules (#FFFFFF) provides a natural structural hierarchy without the need for heavy lines.
- **Content:** Deep slate (#111827) ensures maximum readability for technical data, while the variant gray (#6B7280) handles secondary labels and metadata to prevent visual clutter.

## Typography

This design system utilizes **Geist** for its technical precision and exceptional legibility at small sizes—critical for data-heavy assessment reports. 

- **Headlines:** Use semi-bold weights with slight negative letter-spacing to create a tight, professional appearance for section headers and damage titles.
- **Body Text:** Standardized on a 16px base for desktop to ensure accessibility during long review sessions.
- **Technical Labels:** Small caps or medium-weight 12px labels are used for UI metadata, such as confidence scores and timestamps.

## Layout & Spacing

The layout employs a **Fluid-Fixed Hybrid Grid**. Content is housed in a centered container with a maximum width of 1280px on desktop, while maintaining fluid 12-column flexibility within that container.

- **Rhythm:** A strict 4px baseline grid governs all spacing.
- **Density:** High whitespace in the "Navigation" and "Header" areas transitions to "Medium Density" in the "Assessment Workspace" to keep relevant damage data visible without scrolling.
- **Adaptive Rules:** On mobile, the 12-column grid collapses to a single column with 16px side margins. Cards and photo-viewers become full-bleed to maximize the visual area for damage inspection.

## Elevation & Depth

Hierarchy is established through **Tonal Layering** and **Soft Ambient Shadows**. This system avoids heavy borders in favor of depth cues that feel integrated into the environment.

- **Level 0 (Background):** #F9FAFB. The base canvas.
- **Level 1 (Cards/Surface):** #FFFFFF with a 1px border (#E5E7EB). This is the default state for standard modules.
- **Level 2 (Active/Floating):** Used for modals and active tooltips. Features a soft, diffused shadow: `0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025)`.
- **Level 3 (Overlay):** Used for image zoom views. High-contrast backdrop blur (8px) on the underlying content to focus the user on the specific damage detail.

## Shapes

The design system utilizes a **"Double-Soft" (2xl)** rounding strategy to counteract the coldness of technical data. 

- **Primary Containers:** Large cards and photo containers use a 1rem (16px) radius to create a friendly, modern frame.
- **Interactive Elements:** Buttons and input fields follow the `rounded-lg` (0.5rem) standard for a precise but approachable feel.
- **Indicators:** AI confidence tags and status badges use fully rounded (pill) shapes to distinguish them from actionable buttons.

## Components

### Buttons
- **Primary:** Solid #2563EB with white text. 8px radius. Subtle scale-down effect on click (98%).
- **Secondary:** White background with #E5E7EB border. Used for "Cancel" or "Save Draft" actions.

### Input Fields
- **Standard:** 1px #E5E7EB border with #F9FAFB background. On focus, the border transitions to #2563EB with a 2px outer glow.

### Assessment Cards
- **Structure:** White surface, 16px padding, 16px radius. Includes a "Confidence Score" chip in the top-right corner.
- **Interaction:** Hover state triggers a subtle lift (Elevation Level 2) to indicate the card is selectable for deeper review.

### Status Chips
- **High Confidence:** Light green background with dark green text.
- **Review Required:** Light amber background with dark amber text.
- **Critical Damage:** Light red background with dark red text.

### Image Inspector
- A specialized component featuring a large radius (24px) image container with interactive "Damage Pins" that pulse slightly to draw attention to detected anomalies.