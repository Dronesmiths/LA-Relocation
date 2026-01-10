# TIER 2 NEIGHBORHOOD PAGE TEMPLATE
## Reusable Structure for All Neighborhood Pages

---

## FILE STRUCTURE
```
/[city-name]/[neighborhood-name]/index.html
Example: /long-beach/belmont-shore/index.html
```

---

## CONTENT CHECKLIST (600-900 words total)

### 1️⃣ HERO SECTION
**Elements:**
- H1: `Living in [Neighborhood Name], [City]`
- 1-2 sentence lifestyle hook (unique to this neighborhood)
- Background image showing neighborhood character

**Example:**
```html
<h1>Living in <span style="color:#e63946;">Belmont Shore</span></h1>
<p>Long Beach's most walkable beachside neighborhood, where coastal charm meets vibrant Second Street living.</p>
```

---

### 2️⃣ WHERE THIS NEIGHBORHOOD FITS IN THE CITY
**Purpose:** Establish parent-child relationship with city page

**Content to include:**
- Geographic location within the city
- How it differs from nearby neighborhoods
- Who it's best suited for

**Must include:**
- Internal link back to city page: `← Back to [City] Real Estate Guide`

**Example:**
"Belmont Shore sits on the southeastern edge of Long Beach... Unlike the high-rise urban feel of Downtown Long Beach or the sprawling suburban character of Bixby Knolls, Belmont Shore offers..."

---

### 3️⃣ HOUSING & ARCHITECTURE SNAPSHOT
**Purpose:** Concrete differentiation (prevents duplication)

**Cover:**
- Home styles (bungalows, condos, townhomes, modern, historic)
- General price range language (no exact numbers)
- Ownership vs rental feel
- Lot sizes, architectural character

**This section MUST be different on every neighborhood page.**

---

### 4️⃣ LIFESTYLE & DAY-TO-DAY LIVING
**Purpose:** User intent + engagement

**Cover:**
- Walkability score/feel
- Dining & shopping style
- Parks, recreation, commute
- Quiet vs active vibe
- Beach/nature access

**This is where users "feel" the neighborhood.**

---

### 5️⃣ WHO THIS NEIGHBORHOOD IS BEST FOR
**Purpose:** Intent segmentation

**Format:** Bullet list works best

**Options:**
- Young professionals
- Families with kids
- Empty nesters
- Retirees
- Remote workers
- Investors
- Beach enthusiasts
- Commuters

**Prevents overlap with other neighborhoods.**

---

### 6️⃣ QUICK FAQ (3-5 QUESTIONS MAX)
**Purpose:** Long-tail capture + schema support

**Example questions:**
- Is [Neighborhood] walkable?
- Are homes mostly condos or single-family?
- Is [Neighborhood] good for families?
- How close is it to [landmark/beach/downtown]?
- What's the commute like from [Neighborhood]?

**Rules:**
- ❌ Do NOT reuse city-level FAQs
- ❌ Do NOT overdo this (max 5 questions)
- ✅ Include FAQPage schema markup

---

### 7️⃣ LIGHT CTA (NO HARD SELL)
**Purpose:** Support Tier 3 later without competing

**CTA examples:**
- "Explore homes in [Neighborhood] or view all [City] listings."
- "Ready to find your perfect home in this [adjective] neighborhood?"

**Links to include:**
- → City page
- → City IDX page
- → Contact page (optional)

**NOT allowed:**
- ❌ Lead capture forms
- ❌ "Schedule a showing" buttons
- ❌ Aggressive conversion language

---

## WHAT TIER 2 IS NOT

**DO NOT include:**
- ❌ Full IDX embeds
- ❌ Aggressive lead forms
- ❌ Service language ("we help you buy")
- ❌ Blog-length content (keep it 600-900 words)
- ❌ Keyword stuffing

---

## SCHEMA MARKUP TEMPLATE

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Place",
      "name": "[Neighborhood Name], [City], CA",
      "description": "[Brief neighborhood description]"
    },
    {
      "@type": "RealEstateAgent",
      "@id": "https://larelocation.com/#organization",
      "name": "LA Relocation - Carol Anderson",
      "url": "https://larelocation.com/[city]/[neighborhood]/",
      "image": "https://larelocation.com/wp-content/uploads/2025/10/Carol-Anderson.webp",
      "description": "Expert Realtor serving [Neighborhood] and [City]."
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "[Question 1]",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "[Answer 1]"
          }
        }
      ]
    }
  ]
}
```

---

## BREADCRUMB NAVIGATION

**Always include:**
```html
<div class="breadcrumb">
    <a href="/">Home</a> / <a href="/[city]/">[City]</a> / [Neighborhood]
</div>
```

---

## INTERNAL LINKING STRATEGY

**Required links:**
1. Breadcrumb to city page
2. "Back to [City] Real Estate Guide" in section 2
3. CTA links to city page and/or city IDX
4. Optional: Contact page

**Do NOT link to:**
- Other neighborhood pages (keeps them independent)
- Service pages (not conversion-focused yet)

---

## SUCCESS RULE

**Ask yourself:**
> "How does this page make the city page rank better?"

If you can't answer this, the page shouldn't exist.

**Tier 2 = Support + Specificity, NOT Conversion**

---

## QUICK REFERENCE CHECKLIST

Before publishing, verify:
- [ ] 600-900 word count
- [ ] Breadcrumb navigation included
- [ ] Link back to city page in section 2
- [ ] Unique housing content (not duplicated from city page)
- [ ] Neighborhood-specific FAQs (not city-level)
- [ ] Light CTA (no hard sell)
- [ ] NO IDX embed
- [ ] NO lead forms
- [ ] Schema markup included
- [ ] All internal links working

---

## EXAMPLE NEIGHBORHOODS BY CITY

**Long Beach:**
- Belmont Shore (beach, walkable)
- Naples Island (luxury, waterfront)
- Bixby Knolls (suburban, family)
- Downtown Long Beach (urban, condos)

**Torrance:**
- Hollywood Riviera (coastal, views)
- Old Torrance (historic, walkable)
- West Torrance (schools, family)

**Pasadena:**
- Old Town Pasadena (walkable, dining)
- Bungalow Heaven (historic, Craftsman)
- Linda Vista (hillside, views)

**Santa Clarita:**
- Valencia (master-planned, family)
- Stevenson Ranch (gated, upscale)
- Canyon Country (affordable, spacious)

---

## FINAL NOTES

- Keep it tight, focused, and unique
- Every neighborhood page should feel different
- Support the city page, don't compete with it
- No conversion pressure—that's for Tier 3

**Tier 2 exists to make Tier 1 stronger.**
