---
name: Bangalore Food-Tech Concept Studio
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1b1b1b'
  on-surface-variant: '#5b403f'
  inverse-surface: '#313030'
  inverse-on-surface: '#f3f0ef'
  outline: '#8f6f6e'
  outline-variant: '#e4bebc'
  surface-tint: '#bb162c'
  primary: '#b7122a'
  on-primary: '#ffffff'
  primary-container: '#db313f'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb3b1'
  secondary: '#006e26'
  on-secondary: '#ffffff'
  secondary-container: '#8af793'
  on-secondary-container: '#007328'
  tertiary: '#0051d5'
  on-tertiary: '#ffffff'
  tertiary-container: '#316bf3'
  on-tertiary-container: '#fefcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#8dfa96'
  secondary-fixed-dim: '#71dd7c'
  on-secondary-fixed: '#002106'
  on-secondary-fixed-variant: '#00531b'
  tertiary-fixed: '#dbe1ff'
  tertiary-fixed-dim: '#b4c5ff'
  on-tertiary-fixed: '#00174b'
  on-tertiary-fixed-variant: '#003ea8'
  background: '#fcf9f8'
  on-background: '#1b1b1b'
  surface-variant: '#e5e2e1'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 42px
    letterSpacing: -0.03em
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '800'
    lineHeight: 34px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 30px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 26px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 17px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.04em
  tabular-stat:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 26px
    letterSpacing: -0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style
This design system captures the dynamic, ultra-efficient energy of contemporary urban Indian food technology ecosystems. Built specifically for rapid restaurant concept validation, market viability assessments, and neighborhood feasibility checks across Bangalore micro-markets (such as Indiranagar, Koramangala, and HSR Layout), the aesthetic balances consumer-grade warmth with analytical precision.

The style unites modern food delivery vibrancy with clean, utility-driven transactional design:
- **Tone:** Energetic, decisive, analytically transparent, and localized.
- **Visual Aesthetic:** High-density mobile-first card architecture, tactile tap targets, punchy crimson accents, distinct status badges for viability metrics, and zero-friction anonymous workflows (no login barriers).
- **Emotional Intent:** Instill confidence, speed, and visceral familiarity among restaurateurs, cloud-kitchen operators, and culinary entrepreneurs.

## Colors
The color architecture relies on high-contrast utility signaling inherited from Indian consumer food delivery interfaces, counterbalanced by structured neutral surfaces.

### Core Swatches
- **Primary (`#E23744`):** Delivery Red. Dedicated to primary CTAs, active operational indicators, highlight callouts, and critical interactions.
- **Secondary / Rating Green (`#24963F`):** Represents high probability, profitability upside, positive footfall density, and vegetarian/green validations.
- **Tertiary / Market Blue (`#2563EB`):** Applied for benchmark comparative data, below-market pricing tags, informational alerts, and demographic stats.
- **Caution Amber (`#F2A100`):** Reserved for moderate viability scores, high-competition saturations, and risk alerts.
- **Neutral Primary (`#1C1C1C`):** Deep charcoal for primary typography, dominant headings, and high-emphasis data points.
- **Neutral Secondary (`#696969`):** Warm grey for subheadings, captions, metadata units, and field descriptors.
- **Surface / Canvas:** True pure white (`#FFFFFF`) for root containers and elevated cards, complemented by neutral surface grey (`#F8F8F8`) for section banding, drawer backdrops, and input wells.
- **Stroke / Hairline (`#E8E8E8`):** 1px structural separator for cards, dividers, and unselected chips.

## Typography
Inter delivers crisp geometric legibility at tight mobile viewports and dense information layouts.

### Execution Rules
- **Tabular Figures:** Always apply `font-feature-settings: "tnum" 1` to currency values (INR `₹`), success percentages, margins, and viability indexes to avoid visual layout shifts during live simulation adjustments.
- **Headings:** Headlines are compact, heavy, and punchy (`fontWeight: 700` and `800`) with tight letter tracking to mimic consumer food delivery category cards.
- **Labels & Micro-Badges:** Uppercase is restricted solely to `label-sm` when designating status indicators (e.g., `HIGH DEMAND`, `OVERSATURATED`).

## Layout & Spacing
A dedicated mobile-first fluid layout model designed specifically for responsive web browsers on handheld viewports (360px - 430px base canvas width), constrained on desktop viewports to a centered 480px simulated device frame.

### Layout Rules
- **Base Grid:** Single column fluid layout with a mandatory `1rem` (16px) margin gutter on mobile viewports.
- **Rhythm:** Modular increments of 4px and 8px. Internal card padding is strictly uniform at `1rem` (16px) or `1.25rem` (20px) for highlighted viability summaries.
- **Stacking:** Consecutive analytical cards maintain a vertical gap of `space-md` (16px). Form groups and input fields are spaced by `space-sm` (8px) to `space-md`.
- **Bottom Clearance:** A persistent bottom clearance of `5rem` (80px) is reserved at the base of the viewport to prevent sticky assessment buttons from occluding disclaimer footers.

## Elevation & Depth
Elevation mimics tangible physical order slips, interactive menu selectors, and overlay sheets using clean white layers, muted neutral borders, and warm ambient diffusion.

### Elevation Levels
- **Level 0 (Flat Canvas):** `#F8F8F8` background base with no shadows or borders. Used for page grounding and recessed segmented controls.
- **Level 1 (Card Default):** `#FFFFFF` background with a 1px solid `#E8E8E8` stroke and an ultra-subtle ambient shadow: `0 2px 8px rgba(28, 28, 28, 0.04)`.
- **Level 2 (Interactive Floating Card / Active Chip):** Raised state on tap or dynamic change. Border shifts to `#E23744` (if active) or remains subtle, with `0 6px 16px rgba(28, 28, 28, 0.08)`.
- **Level 3 (Sticky Nav & Drawers):** `#FFFFFF` surfaces with `0 -4px 20px rgba(0, 0, 0, 0.08)` for bottom sheets and floating calculate CTAs. Slide-out drawer navigation utilizes `4px 0 24px rgba(0, 0, 0, 0.12)`.

## Shapes
A friendly, ergonomic geometry that aligns with modern food delivery visual conventions.

### Radii Guidelines
- **Cards & Data Modules:** Unified `1rem` (16px) border radius creates smooth containment for charts, map snapshots, and metric clusters.
- **Inputs & Selection Triggers:** `0.75rem` (12px) to `1rem` (16px) radius for soft, tap-friendly touch bounding boxes.
- **Action Buttons & Chips:** Full pill geometry (`9999px`) for action buttons, filter pills, and category selections to enhance clickability and thumb-reach navigation.
- **Badges & Emoji Containers:** `0.5rem` (8px) for compact tags; circular (`50%`) for avatar initials and cuisine emoji anchors.

## Components

### Action Buttons
- **Primary Pill:** Background `#E23744`, text `#FFFFFF`, font `label-lg`, height `52px`, radius `9999px`, shadow `0 4px 12px rgba(226, 55, 68, 0.25)`. Full width on mobile screens. Active state scales to `0.98`.
- **Secondary / Ghost Pill:** Background `#FFFFFF`, border `1.5px solid #E8E8E8`, text `#1C1C1C`, height `44px`, radius `9999px`.

### Selection & Filter Chips
- **Idle State:** Background `#FFFFFF`, border `1px solid #E8E8E8`, text `#1C1C1C`, padding `8px 16px`, pill-shaped. Accompanied by relevant cuisine food emojis (e.g., ☕ Filter Coffee, 🍛 Biryani, 🍕 Pizza, 🥗 Healthy Bowls).
- **Selected State:** Background `#FFF0F1`, border `1.5px solid #E23744`, text `#E23744`, font `label-md`.

### Viability & Rating Badges
- **High Success Score (Green):** Background `#EAF7EE`, text `#24963F`, border `1px solid #24963F`, font `label-sm`, rounded `6px`. Prefix with star icon or viability percentage.
- **Moderate / Caution (Amber):** Background `#FEF8EC`, text `#F2A100`, border `1px solid #F2A100`.
- **Informational / Benchmark (Blue):** Background `#EFF6FF`, text `#2563EB`, border `1px solid #2563EB`.

### Metric & Concept Cards
- **Structure:** Background `#FFFFFF`, border `1px solid #E8E8E8`, radius `16px`, padding `16px`.
- **Header:** Flex container holding cuisine emoji tag, title, and viability badge.
- **Metric Row:** Tabular font figures for average ticket size (e.g., `₹250 - ₹380`), monthly addressable delivery volume, and rent-to-revenue ratio.

### Input Fields & Steppers
- **Field Container:** Background `#F8F8F8`, active border `1.5px solid #E23744`, radius `12px`, padding `12px 16px`, text `#1C1C1C`, placeholder `#696969`.
- **Rupee Pricing Stepper:** Dual pill stepper `[-] ₹ [+]` with high tactile feedback, explicit Rupee glyph prefixes, and numeric keypad triggering.

### Slide-Out Drawer Menu
- **Container:** Width `85vw` (capped at `360px`), height `100vh`, background `#FFFFFF`, shadow level 3, backdrop blur overlay `rgba(0, 0, 0, 0.5)`.
- **Content:** Bangalore locality switcher (Indiranagar, Koramangala, Whitefield, Jayanagar), concept templates, methodology primer, and data source disclosure. Free of user login or signup options.

### Disclaimer Footer
- **Structure:** Muted section at the end of the assessment canvas. Font `body-sm`, text `#696969`, alignment center, padding `24px 16px`. Explicitly conveys non-advisory operational estimation nature without obstructing core mobile CTAs.