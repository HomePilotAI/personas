/**
 * Room Stylist business logic. Pure functions, no I/O.
 */

const ROOMS = {
  living: {
    zones: ["seating", "media", "side console", "circulation"],
    anchors: ["sofa", "rug", "console", "accent chair"],
  },
  bedroom: {
    zones: ["sleep", "dressing", "reading", "circulation"],
    anchors: ["bed", "rug", "wardrobe", "lamp pair"],
  },
  kitchen: {
    zones: ["prep", "cook", "store", "eat"],
    anchors: ["island", "stools", "pendant", "open shelf"],
  },
  office: {
    zones: ["focus", "video", "storage", "movement"],
    anchors: ["desk", "task chair", "shelving", "task light"],
  },
  diningroom: {
    zones: ["dining", "service", "circulation", "ambience"],
    anchors: ["table", "chairs", "sideboard", "pendant"],
  },
  studio: {
    zones: ["sleep", "work", "lounge", "kitchenette"],
    anchors: ["bed", "rug", "compact desk", "lounge chair"],
  },
};

const PALETTES = {
  warm_minimal: {
    sixty: { name: "ivory", hex: "#F4EFE6" },
    thirty: { name: "warm walnut", hex: "#7A5A3E" },
    ten: { name: "rust", hex: "#B5532A" },
    materials: ["oiled oak", "linen", "boucle", "brushed brass"],
  },
  cool_modern: {
    sixty: { name: "fog", hex: "#D3D7DB" },
    thirty: { name: "ink", hex: "#1F2A33" },
    ten: { name: "ocean", hex: "#1F6FB2" },
    materials: ["smoked glass", "matte steel", "wool flannel", "sandblasted concrete"],
  },
  earth_organic: {
    sixty: { name: "stone", hex: "#C8B79A" },
    thirty: { name: "olive", hex: "#5C6A3C" },
    ten: { name: "clay", hex: "#A8593A" },
    materials: ["limewash", "rattan", "raw cotton", "terracotta"],
  },
  bright_playful: {
    sixty: { name: "chalk", hex: "#F2F2EE" },
    thirty: { name: "marigold", hex: "#E1A93B" },
    ten: { name: "aubergine", hex: "#5C2A4B" },
    materials: ["lacquered ply", "bouclé", "polished chrome", "checkerboard tile"],
  },
};

const SHOPPING_TIERS = [
  { name: "good", note: "Solid silhouette, mid-volume brands. Replaceable in 5-7 years." },
  { name: "better", note: "Better materials, longer warranty, modest brand premium." },
  { name: "heirloom", note: "Solid wood / dense weave / repairable; designed to outlive a move." },
];

function seedFrom(text) {
  let h = 5381;
  for (const c of String(text || "")) h = ((h << 5) + h + c.charCodeAt(0)) >>> 0;
  return h;
}

function pick(arr, seed, offset = 0) {
  return arr[Math.abs(seed + offset) % arr.length];
}

function normalizeRoom(r = "living") {
  const k = String(r).toLowerCase().replace(/\s+/g, "");
  return ROOMS[k] ? k : "living";
}

function normalizePalette(p = "warm_minimal") {
  return PALETTES[p] ? p : "warm_minimal";
}

export function proposeLayout({ room, length_m, width_m, primary_use, options = 3 }) {
  const safeRoom = normalizeRoom(room);
  const r = ROOMS[safeRoom];
  const seed = seedFrom(`${safeRoom}|${length_m || ""}|${width_m || ""}|${primary_use || ""}`);
  const safeOptions = Math.min(Math.max(Number.isInteger(options) ? options : 3, 1), 3);

  const layouts = Array.from({ length: safeOptions }, (_, i) => {
    const focus = pick(r.zones, seed, i);
    const anchor = pick(r.anchors, seed, i + 1);
    const offsetAnchor = pick(r.anchors, seed, i + 2);

    return {
      id: `layout-${i + 1}`,
      focus_zone: focus,
      anchor_piece: anchor,
      arrangement: [
        `Anchor the ${focus} zone around the ${anchor} on the long wall.`,
        `Place the ${offsetAnchor} on the opposite axis to define the secondary zone.`,
        `Leave 90 cm of clear circulation between zones.`,
      ],
      pros: [
        focus === "circulation"
          ? "Maximises through-traffic flow."
          : `Centres daily life on ${focus}.`,
        "Keeps sightlines from the entry clear.",
      ],
      cons: [
        "Requires an outlet within 1.5m of the anchor — check before committing.",
      ],
    };
  });

  return {
    room: safeRoom,
    footprint: { length_m: length_m || null, width_m: width_m || null },
    primary_use: primary_use || null,
    layouts,
    rules_of_thumb: [
      "Define zones before you define style.",
      "Walk the path you'll take 10 times a day; it must be clear.",
      "Anchor with the largest piece first; everything else negotiates with it.",
    ],
  };
}

export function buildPalette({ room, mood }) {
  const safeRoom = normalizeRoom(room);
  const safeMood = normalizePalette(mood);
  const p = PALETTES[safeMood];
  return {
    room: safeRoom,
    mood: safeMood,
    rule: "60% dominant, 30% secondary, 10% accent — apply to walls/large surfaces, soft furnishings, and one sculptural piece respectively.",
    palette: {
      sixty: p.sixty,
      thirty: p.thirty,
      ten: p.ten,
    },
    materials: p.materials,
    pairing_notes: [
      `Use ${p.sixty.name} on the largest surfaces (walls, sofa, rug ground).`,
      `Layer ${p.thirty.name} into upholstery, drapery, or cabinetry.`,
      `Reserve ${p.ten.name} for one sculptural moment per zone — never spread it thin.`,
    ],
  };
}

const ZONE_ITEMS = {
  living: ["sofa", "rug", "side table", "lamp", "art"],
  bedroom: ["bed", "rug", "lamp pair", "throw", "art"],
  kitchen: ["stools", "pendant", "rug runner", "open shelf", "tea set"],
  office: ["desk", "task chair", "shelving", "task light", "rug"],
  diningroom: ["table", "chairs", "sideboard", "pendant", "art"],
  studio: ["bed", "compact desk", "lounge chair", "rug", "lamp"],
};

export function buildShoppingList({ room, palette = "warm_minimal", budget = "balanced" }) {
  const safeRoom = normalizeRoom(room);
  const safePalette = normalizePalette(palette);
  const items = ZONE_ITEMS[safeRoom] || ZONE_ITEMS.living;

  const tiered = items.map((item) => ({
    item,
    tiers: SHOPPING_TIERS.map((t) => ({
      tier: t.name,
      guidance: t.note,
      example: `${item} in ${PALETTES[safePalette].sixty.name} or ${PALETTES[safePalette].thirty.name}`,
    })),
  }));

  return {
    room: safeRoom,
    palette: safePalette,
    budget,
    tiers: SHOPPING_TIERS.map((t) => t.name),
    items: tiered,
    notes: [
      "Pick one heirloom anchor per room; mix the rest across tiers.",
      "Always verify dimensions and return windows before ordering.",
      "Budget 10% buffer for delivery, shims, and the small thing you forgot.",
    ],
  };
}

export const _internals = { ROOMS, PALETTES };
