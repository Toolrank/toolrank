"""Catalogue rules for the bulk supplier feed (used by scripts/dsz_import.py): eligibility, safety exclusions, pricing and category mapping.
Public: contains no costs, supplier names or private data."""
import re, math, datetime

# ---------- safety / regulated exclusions (title + category; some description checks) ----------
R_ADULT = re.compile(r"(?<!concrete )\b(sex|sex toys?|vibrators?|dildos?|butt plugs?|anal|erotic|bdsm|bondage|fetish|nipple clamps?|cock rings?|masturbat\w*|penis|vagina|strap[- ]on|kegel\w*|condoms?)\b", re.I)
R_FOOD = re.compile(r"\b(protein powder|whey protein|dietary supplements?|supplements?|multivitamins?|vitamin (tablets|capsules|gummies)|probiotics?|collagen powder|weight loss (tea|capsules|pills)|herbal tea|loose leaf tea|tea bags?|coffee beans|ground coffee|whole[- ]bean|espresso blend|arabica|robusta|lollies|beef jerky|dog food|cat food|pet food|kibble|dog treats?|cat treats?|fish food|fish flakes|bird ?seed|dental chews?|dried fruit|baby formula|infant formula|chocolates?|wine|beer|cider|spirits|whisk(e)?y|vodka|gin|rum|champagne|sauce|seasonings?|spices?|honey|coffee|tea|snacks?|biscuits|cookies|nuts|almonds)\b", re.I)
R_FOOD_GEN = re.compile(r"\b(protein powder|whey protein|dietary supplements?|nutritional supplements?|supplements? (capsules|tablets|powder)|multivitamins?|vitamin (tablets|capsules|gummies)|probiotics?|collagen powder|weight loss (tea|capsules|pills)|herbal tea|loose leaf tea|tea bags?|coffee beans|ground coffee|whole[- ]bean|espresso blend|lollies|beef jerky|dog food|cat food|pet food|kibble|dog treats?|cat treats?|fish food|fish flakes|bird ?seed|dental chews?|dried fruit|baby formula|infant formula)\b", re.I)
R_FOOD_OK = re.compile(r"\b(containers?|dispensers?|holders?|maker|machines?|grinders?|bowls?|feeders?|storage|jars?|canisters?|clips?|scoops?|moulds?|molds?|trays?|cups?|mugs?|grater|press|tamper|frother|kettles?|pots?|teapots?|scales?|organi[sz]ers?|racks?|stands?|boxe?s?|tins?|bottles?|warmers?|blenders?|fountains?|toys?|mats?|filters?|caddy|tumblers?|openers?|chillers?|decanters?|aerators?|stoppers?|glass|glasses|glassware|infusers?|strainers?|spoons?|towels?|aprons?|costumes?|lamps?|lights?|stickers?|posters?|bags?|cases?|baskets?|books?|games?|puzzles?|plush|keyrings?|keychains?|cutters?|slicers?|peelers?|thermometers?|nets?|pouch(es)?|wraps?|sealers?|steriliser|sterilizer|sifters?|signs?|tables?|carts?|trolleys?|kegs?|taps?|coolers?|fridges?|sets?|accessories|cabinets?|shelf|shelves|decor|decorations?|ornaments?|candles?|soap|lotion|serum|cream|shampoo|conditioner|scrub|bath|perfume|fragrance|diffuser|oil burner|wax melts?|sofa|chair|cushion|rug|curtain|fabric|dress|shirt|t-shirt|hoodie|socks?)\b", re.I)
FOOD_HAMPERS = ("Beer Hampers", "Chocolate & Sweets Hampers", "Gourmet Food Hampers", "Tea & Coffee Hampers", "Wine & Champagne Hampers")
R_QTY = re.compile(r"\b\d+(\.\d+)?\s?(g|kg|mg|ml|l|grams?)\b|\b(powder|granules|capsules|tablets|organic|dried|extract|roast|grind)\b", re.I)
R_LIVE = re.compile(r"\blive (fish|plants?|insects?|crickets?|worms?|bait|animals?|birds?|chicks?|shrimp|snails?|mealworms?|reptiles?)\b|\bliving (aquarium )?plants?\b", re.I)
R_LIVE_OK = re.compile(r"\b(containers?|buckets?|box|boxes|holders?|feeders?|traps?|dish|cages?|aerators?|pumps?|tanks?|spikes|watering|cases?|bags?|nets?|kits?|tools?)\b", re.I)
R_MED_T = re.compile(r"\b(medical|therapeutic|therapy|pain relief|relieves? (?:\w+ ){0,3}pain|relieve (?:arthritis|joint)|arthritis|carpal tunnel|tens (unit|machine)|tens/ems|ems muscle|electrotherapy|hearing aids?|blood pressure|oximeters?|glucose|nebuli[sz]ers?|stethoscopes?|wheelchairs?|walking frames?|rollators?|commodes?|incontinence|orthopa?edic|orthosis|posture correctors?|compression stockings?|surgical|syringes?|hypodermic|scalpels?|catheters?|infrared lamp|red light (therapy|device)|acupuncture|cupping|lice treatment|insulin|diabetic|sciatica|plantar fasciitis|scoliosis|hernia|splints?|cures?|healing|anti[- ]?snoring|snore stoppers?|weight loss|fat burn\w*|slimming|detox|magnetic bracelets?|copper bracelets?|ear ?wax remov\w*)\b", re.I)
R_MED_D = re.compile(r"\b(TGA|ARTG|therapeutic goods|clinically proven|medical[- ]grade|medical device|pain relief|relieves? (?:\w+ ){0,3}pain|relief from (?:\w+ ){0,2}pain|treats? (?:arthritis|insomnia|anxiety|depression|acne|eczema|psoriasis)|cures?)\b", re.I)
MED_D_CATS = ("Health & Beauty", "Adult Products")
MED_LEAVES = ("Monitoring & Testing", "Supports & Braces", "Mobility & Accessibility", "Pharmaceutical Supplies", "Medical Tape & Bandages", "Pet Medical Collars", "Incontinence Care", "Test Kits")
R_WEAPON = re.compile(r"\b(swords?|katanas?|machetes?|daggers?|bayonets?|crossbows?|slingshots?|catapults?|blowguns?|nunchaku|nunchucks?|knuckle ?dusters?|brass knuckles?|throwing (stars?|knives|knife|axes?)|shuriken|stun ?guns?|tasers?|pepper spray|batons?|airsoft|bb guns?|gel[- ]?(ball )?blasters?|water bead blasters?|orbeez blasters?|pellet guns?|air rifles?|air pistols?|rifle ?scopes?|riflescopes?|firearms?|ammunition|gun holsters?|pistol holsters?|tactical vests?|plate carriers?|body armou?r|bullet ?proof|stab ?proof|spear ?guns?|harpoons?|compound bows?|recurve bows?|longbows?|archery arrows|broadheads?|karambits?|bowie|switchblades?|flick knife|butterfly knife|balisong|tomahawks?|hunting knife|tactical knife|survival knife|combat knife|military knife|pocket knife|folding knife|tactical pens?|kubotan|self[- ]defen[cs]e|laser pointers?|toy guns?|cap guns?|replica guns?|revolvers?|shotguns?)\b", re.I)
R_GUN = re.compile(r"\b(guns?|pistols?)\b", re.I)
GUN_OK = re.compile(r"\b(icing|decorating|cookie|press|watering|tufting|dust|dusting|removing|blower|cleaner|caulking|massage|glue|heat|massage|massager|nail|nailer|spray|paint|grease|water|staple|stapler|caulking|caulk|bubble|soldering|sealant|silicone|foam|rivet|tag|tagging|price|label|blow|temperature|thermometer|ir|infrared|impact|screw|lube|cleaning|wash|washer|jet|mist|misting|fogger|steam|hot air|tyre|tire|inflator|fascia|percussion|muscle|sand|sandblast|blasting|sealing|cartridge|drywall|pipe|spot|welding|mig|tig|plasma|solder|labeller|tape|sewing|air|snow|confetti|smoke|fog|hot melt|squirt|grout|caulk(ing)?|dusting|pressure)[- ]*(guns?|pistols?)\b", re.I)
R_KNIFE = re.compile(r"\bkni(fe|ves)\b", re.I)
KNIFE_OK = re.compile(r"\b(kitchen|chef|chefs|chef's|bread|paring|fillet|filleting|steak|cheese|carving|santoku|cleaver|butter|cake|palette|pizza|boning|nakiri|utility|putty|stanley|craft|hobby|box cutter|cutter|snap[- ]off|retractable|plaster|scraper|drywall|carpet|roofing|linoleum|vinyl|block|sharpener|sharpening|stand|holder|rack|magnetic|set|cutlery|fork|spoon|table|dinner|serrated|vegetable|fruit|peeling|oyster|sushi|deba|yanagiba|gyuto|bbq|grill|pruning|grafting|garden|weeding|sickle|mower|multi[- ]?tool|wood ?carving|whittling|leather|crafts?|pumpkin|mezzaluna|electric knife|blades? for|replacement blades?)\b", re.I)
KNIFE_CATS = ("Kitchenware", "Kitchen Knives", "Cutlery", "Tools >", "Cutters", "Putty Knives", "Garden")
R_GAS = re.compile(r"\b(gas|lpg|propane|butane)\b", re.I)
GAS_OK = re.compile(r"\b(gas[- ]?(springs?|struts?|lift(ed|ing)?|shocks?|masks?|detectors?|leak detectors?|piston|assisted|cylinder chair)|gaslift|gas-lift)\b", re.I)
GAS_LEAVES = ("Patio Heaters", "Gas & Oil Heaters", "Cooktops & Stoves", "Cooking Ranges", "BBQs & Accessories", "Camping Appliances", "Fire Pits", "Industrial Heaters")
GAS_APPL = re.compile(r"\b(heaters?|stoves?|cooktops?|burners?|bbqs?|barbecues?|grills?|ovens?|lamps?|lanterns?|torch(es)?|hoses?|regulators?|valves?|cylinders?|bottles?|fittings?|adapters?|adaptors?|hot water|fire ?pits?|cookers?|ranges?|fryers?|smokers?|blowers?|lighters?|refill|canisters?|cartridges?|appliances?|water heaters?|tanks?)\b", re.I)
GAS_ACC = re.compile(r"\b(covers?|mats?|pans?|woks?|knobs?|kettles?|liners?|splatter|cleaning|brush(es)?|griddles?|trays?|toppers?|racks?|grates?|thermometers?|tools? set|utensils?|pots?|cookware|cap\b|pedal)\b", re.I)
R_GAS_FREE = re.compile(r"\b(charcoal|electric|wood[- ]?fired|pellet|diesel|induction|kerosene)\b", re.I)
GAS_CERT = re.compile(r"\b(AGA[- ]?(certified|approved|certification)|AGA\b|AS/?NZS ?5263|AS ?4565|AS/?NZS ?4565|SAI Global certified|Vipac certified|IAPMO|GAMAA)", re.I)
R_REG = re.compile(r"\b(vapes?|vaping|e-?cig(arette)?s?|e-liquids?|nicotine|shisha|hookahs?|bongs?|fireworks?|tattoo (inks?|machines?|guns?|needles?|kits?|pens?|cartridges?)|permanent makeup|micro ?blading|teeth whitening|contact lens(es)?|radar detectors?|signal jammers?|jammers?|lock ?picks?|lock ?picking|mosquito coils?|insecticides?|herbicides?|pesticides?|rat poison|rodenticides?|weed killers?|glyphosate|insect (spray|repellent spray)|fly spray|bug spray|pool chlorine|chlorine tablets|baby car seats?|child car seats?|booster seats?|car capsules?|child restraints?)\b", re.I)
REG_LEAVES = ("Herbicides", "Fertilisers")
R_HELMET = re.compile(r"\b(bike|bicycle|cycling|motorcycle|motorbike|scooter|skate|ski|snowboard|kids?'?|equestrian|riding)\b.*\bhelmets?\b|\bhelmets?\b.*\b(bike|bicycle|cycling|motorcycle|motorbike|scooter|skate|ski)\b", re.I)
HELMET_CERT = re.compile(r"AS/?NZS ?(2063|1698)|AS ?1698|ECE ?22", re.I)

def exclusion(title, cat, desc):
    """First matching safety/regulatory rule, or None."""
    parts = [p.strip() for p in cat.split(">")]; top = parts[0]; leaf = parts[-1]
    t = title
    if top == "Adult Products" or R_ADULT.search(t): return "adult"
    if R_LIVE.search(t) and not R_LIVE_OK.search(t): return "live_animals"
    if top == "Food & Beverage" or leaf in FOOD_HAMPERS or leaf in ("Vitamins & Supplements", "Cat Food", "Dog Food", "Fish Food"):
        if (R_FOOD_GEN.search(t) or R_FOOD.search(t) or R_QTY.search(t)) and not R_FOOD_OK.search(t): return "food_supplements"
    if R_FOOD_GEN.search(t) and not R_FOOD_OK.search(t): return "food_supplements"
    if R_WEAPON.search(t): return "weapons_knives"
    if R_GUN.search(re.sub(r"(?i)gun ?metal|gunmetal", "", t)) and not GUN_OK.search(t): return "weapons_knives"
    if R_KNIFE.search(t) and not (KNIFE_OK.search(t) or any(k in cat for k in KNIFE_CATS)): return "weapons_knives"
    if R_MED_T.search(t): return "medical_therapeutic"
    if top in MED_D_CATS and R_MED_D.search(desc): return "medical_therapeutic"
    if leaf in MED_LEAVES and re.search(r"\b(brace|support|test|monitor|medic\w*|pill|bandage|wound|recovery|cone|walker|walking|cane|crutch\w*|blood|pulse|health)\b", t, re.I): return "medical_therapeutic"
    if not GAS_OK.search(t) and not GAS_ACC.search(t) and ((R_GAS.search(t) and GAS_APPL.search(t)) or (leaf in GAS_LEAVES and R_GAS.search(desc) and not R_GAS_FREE.search(t + " " + desc[:400]))):
        if not (GAS_CERT.search(t) or GAS_CERT.search(desc)): return "gas_not_au_certified"
    if R_REG.search(t) or (leaf in REG_LEAVES and re.search(r"\b(fertili[sz]ers?|plant food|nutrients?|diatomaceous|herbicides?|weed ?killer|pesticides?|insecticides?|sprays? concentrate)\b", t, re.I)): return "other_regulated"
    if R_HELMET.search(t) and not re.search(r"\bhelmets? (bags?|locks?|liners?|holders?|hooks?|racks?|stands?|covers?|visors?|mounts?|lights?|cameras?|stickers?|straps?|pads?|hangers?|display)|\b(bags?|locks?|liners?|holders?|hooks?|racks?|covers?|lights?|cameras?)\b.*helmet|helmet.*\b(bag|lock|liner|holder|hook|rack|cover|light|camera)\b", t, re.I) and not HELMET_CERT.search(desc + " " + t): return "other_regulated"
    return None

# ---------- pricing ----------
STRIPE_PCT, STRIPE_FIX, MARKUP, FLOOR = 0.0165, 0.30, 1.25, 0.05  # 25% markup on cost incl. delivery (owner, 2 Nov 2026); 5% minimum margin after Stripe fees
def up95(x):
    """Round UP to the next price ending in .95."""
    n = math.floor(x)
    v = n + 0.95
    if v + 1e-9 < x: v = n + 1.95
    return round(v, 2)
def down95_below(x):
    """Highest .95 price strictly below x."""
    n = math.floor(x)
    v = n + 0.95
    while v >= x - 1e-9: v -= 1
    return round(v, 2)
def net(price): return price * (1 - STRIPE_PCT) - STRIPE_FIX
def sell_price(cost_total, rrp=None):
    """(price, reason). cost_total = supplier price incl. GST + Sydney metro delivery.
    price = (cost_total x MARKUP + Stripe fixed fee) / (1 - Stripe %), rounded UP to .95. Where that reaches the supplier RRP, the highest .95
    price below RRP is used instead, provided it still leaves FLOOR (5%) margin after Stripe fees; otherwise the item is not listed."""
    base = cost_total * MARKUP
    p = up95((base + STRIPE_FIX) / (1 - STRIPE_PCT))
    if rrp and p >= rrp:
        p = down95_below(rrp)
        if p <= 0 or net(p) < cost_total * (1 + FLOOR): return None, "price_at_or_above_rrp"
        return p, "capped_below_rrp"
    return p, "formula"
def margin_pct(price, cost_total): return round((net(price) - cost_total) / cost_total * 100, 1)

def num(s):
    try: return float(str(s).replace(",", "").strip())
    except Exception: return None
def placeholder_rate(v): return v is None or v >= 9000

# ---------- categories ----------
NEW_CATS = [
    ("furniture", "Furniture", "Beds, sofas, tables, chairs and outdoor settings."),
    ("home-living", "Home & living", "Bedding, decor, lighting, rugs and storage."),
    ("kitchen", "Kitchen", "Cookware, utensils, small appliances and bins."),
    ("bathroom", "Bathroom", "Vanities, tapware, showers and accessories."),
    ("appliances", "Appliances", "Heating, cooling, fridges, laundry and air care."),
    ("electronics", "Electronics", "Computer, phone, audio, camera and TV gear."),
    ("office", "Office", "Desks, chairs, stationery and packaging."),
    ("sports-fitness", "Sports & fitness", "Gym, bikes, water sports, fishing and more."),
    ("pets", "Pets", "Beds, crates, toys, aquariums and farm supplies."),
    ("baby-kids", "Baby & kids", "Nursery, kids furniture, clothing and feeding."),
    ("toys-games", "Toys & games", "Toys, ride-ons, puzzles, games and crafts."),
    ("health-beauty", "Health & beauty", "Hair, makeup, skincare and personal care."),
    ("fashion", "Fashion", "Clothing, shoes, bags, jewellery and travel."),
    ("party-gifts", "Party & gifts", "Christmas, costumes, party supplies and gifts."),
]
L2 = {
 "Appliances > Air Conditioners": "appliances", "Appliances > Aroma Diffusers & Humidifiers": "appliances", "Appliances > Fans": "appliances",
 "Appliances > Fridges & Freezers": "appliances", "Appliances > Heaters": "appliances", "Appliances > Kitchen Appliances": "kitchen",
 "Appliances > Other Cleaning Appliances": "cleaning", "Appliances > TV": "electronics", "Appliances > Vacuum Cleaners": "cleaning",
 "Appliances > Washers, Dryers & Irons": "appliances",
 "Audio & Video > Musical Instrument & Accessories": "music-gear", "Audio & Video > Photography": "electronics",
 "Audio & Video > Projectors & Accessories": "electronics", "Audio & Video > Speakers": "electronics",
 "Auto Accessories > 4WD & Recovery": "automotive", "Auto Accessories > Auto Accessories Others": "automotive",
 "Baby & Kids > Baby & Kid's Toys": "toys-games", "Baby & Kids > Ride On Cars, Go-karts & Bikes": "toys-games",
 "Commercial > Commercial Others": "office", "Commercial > Packaging": "office",
 "Electronics > Business & Home Security": "safety", "Electronics > Printers": "office", "Electronics > Printer Accessories & Supplies": "office",
 "Food & Beverage > Alcoholic Beverages": "kitchen", "Food & Beverage > Pantry": "kitchen",
 "Furniture > Office": "office", "Furniture > Bathroom": "bathroom",
 "Gift & Novelty > Books": "party-gifts", "Gift & Novelty > DVDs, CDs and Blurays": "party-gifts", "Gift & Novelty > Games": "toys-games", "Gift & Novelty > Novelty": "party-gifts",
 "Hampers > Gift Hampers": "party-gifts",
 "Home & Garden > Artificial Plants": "home-living", "Home & Garden > BBQ": "bbq-camping", "Home & Garden > Bathroom Accessories": "bathroom",
 "Home & Garden > Bedding": "home-living", "Home & Garden > Curtains": "home-living", "Home & Garden > DIY": "building", "Home & Garden > Decor": "home-living",
 "Home & Garden > Firepits": "bbq-camping", "Home & Garden > Fountains": "garden", "Home & Garden > Garden Beds": "garden", "Home & Garden > Garden Lights": "garden",
 "Home & Garden > Garden Tools": "garden", "Home & Garden > Gate Openers": "hardware", "Home & Garden > Greenhouses": "garden", "Home & Garden > Hammocks": "bbq-camping",
 "Home & Garden > Hobbies": "toys-games", "Home & Garden > Home Office Accessories": "office", "Home & Garden > Kitchen Bins": "kitchen", "Home & Garden > Kitchenware": "kitchen",
 "Home & Garden > Laundry & Cleaning": "cleaning", "Home & Garden > Lighting": "home-living", "Home & Garden > Pool & Accessories": "garden", "Home & Garden > Rugs": "home-living",
 "Home & Garden > Scales": "home-living", "Home & Garden > Shading": "garden", "Home & Garden > Solar Panels": "garden", "Home & Garden > Storage": "home-living",
 "Home & Garden > Travel": "fashion", "Home & Garden > Wall Art": "home-living",
 "Outdoor Recreation > Camping": "bbq-camping", "Outdoor Recreation > Iceboxes & Coolers": "bbq-camping", "Outdoor Recreation > Picnic": "bbq-camping",
 "Outdoor Recreation > Boating": "sports-fitness", "Outdoor Recreation > Fishing": "sports-fitness", "Outdoor Recreation > Snow Sports": "sports-fitness", "Outdoor Recreation > Water Sports": "sports-fitness",
 "Pet Care > Pest Control": "garden",
 "Tools > Air Compressor": "power-tools", "Tools > Industrial Tools": "hand-tools", "Tools > Other Tools": "hand-tools", "Tools > Power Tools": "power-tools",
 "Tools > Pumps": "garden", "Tools > Tools Storage": "workshop-storage",
}
TOP = {"Auto Accessories": "automotive", "Baby & Kids": "baby-kids", "Electronics": "electronics", "Fashion": "fashion", "Furniture": "furniture",
       "Health & Beauty": "health-beauty", "Occasions": "party-gifts", "Pet Care": "pets", "Sports & Fitness": "sports-fitness", "Home & Garden": "home-living",
       "Appliances": "appliances", "Tools": "hand-tools", "Outdoor Recreation": "bbq-camping", "Audio & Video": "electronics", "Commercial": "office", "Gift & Novelty": "party-gifts"}
LEAF = {  # full-path overrides
 "Audio & Video > Musical Instrument & Accessories > CDs & Vinyl": "party-gifts",
 "Commercial > Commercial Others > Commercial Cleaning Equipment": "cleaning", "Commercial > Commercial Others > Distilling & Brewing": "kitchen",
 "Commercial > Commercial Others > Fencing & Barriers": "building", "Commercial > Commercial Others > Pharmaceutical Supplies": "health-beauty",
 "Commercial > Commercial Others > Tattoo Suppliers": "health-beauty",
 "Gift & Novelty > Games > VR Games": "electronics", "Gift & Novelty > Games > Video Games": "electronics",
 "Health & Beauty > Health & Wellbeing > First Aid Kits": "safety", "Health & Beauty > Health & Wellbeing > Protective Equipment": "safety",
 "Home & Garden > Artificial Plants > Artificial Grass": "garden", "Home & Garden > Decor > Garden Ornaments": "garden",
 "Home & Garden > DIY > Door Hardware": "hardware", "Home & Garden > DIY > Hardware Hooks": "hardware", "Home & Garden > DIY > Wall Plates & Covers": "hardware",
 "Home & Garden > DIY > Dollhouses": "toys-games", "Home & Garden > Lighting > Outdoor Lights": "garden",
 "Home & Garden > Pool & Accessories > Beach Towels": "home-living", "Home & Garden > Storage > Sheds": "garden",
 "Home & Garden > Storage > Storage Cabinets & Lockers": "workshop-storage",
 "Tools > Industrial Tools > Heat Guns": "power-tools", "Tools > Industrial Tools > Saws": "power-tools", "Tools > Industrial Tools > Saw Accessories": "power-tools",
 "Tools > Industrial Tools > Ladders & Scaffolding": "building", "Tools > Industrial Tools > Masonry Tools": "building", "Tools > Industrial Tools > Lifts & Hoists": "workshop-storage",
 "Tools > Industrial Tools > Traffic Control & Parking Tools": "safety", "Tools > Industrial Tools > Work Safety Protective Equipment": "safety",
 "Tools > Industrial Tools > Transformers & Regulators": "hardware", "Tools > Industrial Tools > Water Filtration Accessories": "hardware",
 "Tools > Other Tools > Power & Electrical Supplies": "hardware", "Tools > Other Tools > Tape": "hardware",
 "Tools > Other Tools > Drill & Screwdriver Accessories": "power-tools", "Tools > Other Tools > Sanding Accessories": "power-tools", "Tools > Other Tools > Tool Blades": "power-tools",
 "Tools > Power Tools > Chainsaws": "garden", "Tools > Power Tools > Outdoor Power Equipment": "garden", "Tools > Power Tools > Painting Tools": "building",
 "Pet Care > Farm Supplies > Fencing": "garden",
}
# Junk-drawer supplier categories: re-home items by title keywords (first match wins).
NOISY = {"Wellness Accessories", "Sleeping Aids", "Mobility & Accessibility", "Other Hampers", "Self Care Hampers", "Baby Hampers", "Tattoo Suppliers",
         "Pharmaceutical Supplies", "Medical Tape & Bandages", "Heating Pads", "Back Care", "Camping Appliances", "Monitoring & Testing", "Protective Equipment",
         "Fish Food", "Novelty Gifts", "Retail", "Office Supplies", "Automotive Decor", "Supports & Braces", "Teas & Accessories", "Drinks", "Condiments & Sauces", "Seasonings & Spices"}
KW = [
 (r"\b(sunglass(es)?|eyeglass|reading glasses|blue light glasses|goggles? for (men|women))\b", "fashion", "Sunglasses & Eyewear"),
 (r"\b(watch band|watch strap|smart ?watch|earbuds?|headphones?|charger|usb|hdmi|bluetooth|phone (case|holder|stand)|power bank|cable)\b", "electronics", "Gadgets & Accessories"),
 (r"\b(car|vehicle|auto|truck|motorcycle|motorbike)\b", "automotive", "Car Accessories"),
 (r"\b(dog|cat|pet|puppy|kitten|aquarium|fish tank|bird cage|hamster|rabbit)\b", "pets", "Pet Accessories"),
 (r"\b(baby|toddler|infant|nursery)\b", "baby-kids", "Baby Accessories"),
 (r"\b(wine|teapot|tea ?cup|mug|tumbler|kettle|coffee|cocktail|bar tools?|decanter|drinkware|glassware|tea (set|tray|infuser|strainer)|infuser)\b", "kitchen", "Drinkware & Tea"),
 (r"\b(candle|vase|ornament|figurine|wall decor|cushion|throw|photo frame|picture frame|clock|incense|diffuser|air freshener)\b", "home-living", "Decor"),
 (r"\b(flower ?pot|planter|garden|plant stand|seed)\b", "garden", "Gardening Accessories"),
 (r"\b(tent|camping|hiking|lantern|poncho|sleeping bag|backpack|outdoor)\b", "bbq-camping", "Camping Accessories"),
 (r"\b(yoga|gym|fitness|exercise|resistance band|dumbbell|sports?|bike|bicycle|swim)\b", "sports-fitness", "Fitness Accessories"),
 (r"\b(storage box|organi[sz]er|basket|shelf|rack|hook|hanger)\b", "home-living", "Storage & Organisation"),
 (r"\b(makeup|cosmetic|nail|lash|eyelash|hair|beauty|skin|facial|manicure)\b", "health-beauty", "Beauty Tools"),
 (r"\b(gift|keychain|keyring|novelty)\b", "party-gifts", "Novelty Gifts"),
 (r"\b(tool|drill|screwdriver|wrench|plier|spanner|tape measure)\b", "hand-tools", "Hand Tools"),
]
KWC = [(re.compile(a, re.I), b, c) for a, b, c in KW]
def clean_sub(s):
    s = re.sub(r"\s+", " ", s).strip()
    return s[:1].upper() + s[1:]
def map_category(cat, title):
    parts = [p.strip() for p in cat.split(">")]
    top, l2 = parts[0], " > ".join(parts[:2]); leaf = parts[-1] if len(parts) > 2 else parts[-1]
    if leaf in NOISY:
        for rx, c, s in KWC:
            if rx.search(title): return c, s
    c = LEAF.get(cat) or L2.get(l2) or TOP.get(top) or "home-living"
    return c, clean_sub(leaf)

# ---------- de-duplication (colour/size variants of the same product) ----------
COLORS = set("""black white grey gray silver gold red blue green yellow orange pink purple brown beige cream ivory navy khaki charcoal natural walnut oak teal
turquoise rose multicolour multicolor multi clear transparent burgundy maroon apricot camel tan mint lavender lilac olive champagne bronze copper coral aqua
rainbow light dark sky royal wine coffee chocolate violet magenta fuchsia nude sand stone taupe mustard emerald jade cyan indigo""".split())
SIZES = set("xxs xs s m l xl xxl xxxl 2xl 3xl 4xl 5xl 6xl 7xl 8xl small medium large size sz eu us uk au one osfa".split())
def dedupe_key(title):
    w = re.sub(r"[^a-z0-9]+", " ", title.lower()).split()
    return " ".join(x for x in w if x not in COLORS and x not in SIZES)
