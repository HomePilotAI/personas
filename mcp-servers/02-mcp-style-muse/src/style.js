/**
 * Style Muse business logic. Pure functions, no I/O.
 *
 * Returns deterministic-but-varied outfit suggestions and
 * before/after variants without claiming ownership of any specific
 * brand or product — the persona is a stylist, not a shopper.
 */

const PALETTES = {
  warm: {
    base: ["camel", "ivory", "rust"],
    accent: "gold",
    feel: "grounded, sun-soft",
  },
  cool: {
    base: ["slate", "fog", "ink"],
    accent: "silver",
    feel: "crisp, considered",
  },
  bold: {
    base: ["black", "scarlet"],
    accent: "white",
    feel: "high-contrast, decisive",
  },
  pastel: {
    base: ["butter", "mint", "blush"],
    accent: "pearl",
    feel: "airy, romantic",
  },
  earth: {
    base: ["olive", "stone", "clay"],
    accent: "brass",
    feel: "tactile, lived-in",
  },
};

const TOPS = {
  business: ["a structured blazer", "a crisp button-down", "a fine-knit turtleneck"],
  casual: ["a soft tee", "a relaxed boxy shirt", "a textured henley"],
  date: ["a silk camisole", "a fitted knit", "a slip top under a sharp jacket"],
  party: ["a satin top", "a sequinned tee", "a fitted bodysuit"],
  outdoor: ["a layered hoodie", "a packable shell", "a thermal base layer"],
  travel: ["a soft merino tee", "a wrinkle-resistant overshirt", "a relaxed knit"],
};

const BOTTOMS = {
  business: ["tailored trousers", "a midi pencil skirt", "wide-leg slacks"],
  casual: ["straight-leg jeans", "drawstring trousers", "tailored shorts"],
  date: ["a slip skirt", "dark slim jeans", "wide-leg trousers"],
  party: ["a leather mini", "high-waisted satin trousers", "fitted black jeans"],
  outdoor: ["technical pants", "stretch joggers", "performance shorts"],
  travel: ["wrinkle-resistant pants", "a soft jersey skirt", "modal jeans"],
};

const SHOES = {
  business: ["pointed loafers", "block-heel pumps", "leather derbies"],
  casual: ["clean white sneakers", "minimal sandals", "low-top runners"],
  date: ["strappy heels", "polished mules", "ankle boots"],
  party: ["statement heels", "patent loafers", "metallic boots"],
  outdoor: ["trail runners", "waterproof boots", "supportive low-tops"],
  travel: ["cushioned sneakers", "easy-on loafers", "soft-sole flats"],
};

const ACCENTS = [
  "a textured belt to define the waist",
  "stacked thin chains",
  "one architectural earring",
  "a structured top-handle bag",
  "a soft scarf knotted at the neck",
  "a single bold ring",
];

const ALLOWED_OCCASIONS = Object.keys(TOPS);
const ALLOWED_VIBES = Object.keys(PALETTES);

function seedFrom(text) {
  let h = 5381;
  for (const c of String(text || "")) h = ((h << 5) + h + c.charCodeAt(0)) >>> 0;
  return h;
}

function pick(arr, seed, offset) {
  return arr[Math.abs(seed + offset) % arr.length];
}

function normalizeOccasion(o = "casual") {
  const k = String(o).toLowerCase();
  return ALLOWED_OCCASIONS.includes(k) ? k : "casual";
}

function normalizeVibe(v = "earth") {
  const k = String(v).toLowerCase();
  return ALLOWED_VIBES.includes(k) ? k : "earth";
}

export function buildOutfit({ occasion, vibe, weather, anchor_piece }) {
  const occ = normalizeOccasion(occasion);
  const vb = normalizeVibe(vibe);
  const seed = seedFrom(`${occ}|${vb}|${weather || ""}|${anchor_piece || ""}`);
  const palette = PALETTES[vb];

  const top = pick(TOPS[occ], seed, 0);
  const bottom = pick(BOTTOMS[occ], seed, 1);
  const shoe = pick(SHOES[occ], seed, 2);
  const accent = pick(ACCENTS, seed, 3);
  const accent2 = pick(ACCENTS, seed, 5);

  const weatherNote =
    weather && /cold|rain|snow/i.test(weather)
      ? "Add a long coat and a warm scarf for the temperature."
      : weather && /hot|warm/i.test(weather)
        ? "Drop the jacket; let the base layer breathe."
        : null;

  return {
    occasion: occ,
    vibe: vb,
    palette,
    anchor_piece: anchor_piece || null,
    pieces: {
      top,
      bottom,
      shoes: shoe,
      outerwear: occ === "business" ? "a tailored coat in a base palette tone" : null,
      accents: [accent, accent2],
    },
    styling_notes: [
      `Lean into the ${palette.feel} feel of the palette.`,
      "Tuck the top loosely so the silhouette stays soft.",
      "Pick one accent, not three — let the outfit breathe.",
      ...(weatherNote ? [weatherNote] : []),
      ...(anchor_piece
        ? [`Build around your ${anchor_piece}; everything else is supporting cast.`]
        : []),
    ],
    avoid: [
      "matching every metal to the same finish — a small mismatch reads more deliberate",
      "more than two prints in one look",
    ],
  };
}

const VARIANT_AXES = ["palette", "shoe", "silhouette", "layer", "accent"];

const VARIANT_MOVES = {
  palette: (vb) => `swap the palette to a ${vb === "warm" ? "cool" : "warm"} register`,
  shoe: () => "switch the shoes for a contrasting category (sneaker ↔ heel ↔ boot)",
  silhouette: () => "reshape the silhouette: relaxed → tailored, or vice versa",
  layer: () => "add or remove one outer layer to change the proportion",
  accent: () => "swap the accent piece for one with the opposite weight",
};

export function buildVariants({ base_look, count = 3 }) {
  if (!base_look || typeof base_look !== "string") {
    throw new Error("base_look is required");
  }
  const safeCount = Math.min(Math.max(Number.isInteger(count) ? count : 3, 1), 5);
  const seed = seedFrom(base_look);

  const variants = Array.from({ length: safeCount }, (_, i) => {
    const axis = VARIANT_AXES[(seed + i) % VARIANT_AXES.length];
    const move = VARIANT_MOVES[axis](pick(ALLOWED_VIBES, seed, i));
    return {
      id: `variant-${i + 1}`,
      axis,
      change: move,
      before: base_look,
      after: `${base_look} — but ${move}`,
      keep_one_thing: "Anchor on one element of the original so the user can see what changed.",
    };
  });

  return {
    base_look,
    rule: "Switch one element at a time so the before/after stays legible.",
    variants,
  };
}

export const _internals = {
  ALLOWED_OCCASIONS,
  ALLOWED_VIBES,
  PALETTES,
};
