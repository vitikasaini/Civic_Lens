"""
Text dataset generator for CivicLens V1.0.
Generates 200 realistic, diverse citizen complaints per category (800 total)
covering the 4 civic issue categories:
1. Potholes / Damaged Roads
2. Garbage Accumulation
3. Waterlogging / Drainage Problems
4. Streetlight Faults

Uses combinatorial templates with diverse municipal vocabulary, varied lengths,
severity cues, and colloquial citizen expressions.
Documented as synthetic data per Decision 4 in docs/decisions.md.
"""

import random
import pandas as pd
from pathlib import Path

# Seed for deterministic reproducibility
random.seed(42)

POTHOLE_TEMPLATES = [
    "{severity_prefix} pothole on {location}. {impact}",
    "There is a {adj} crater on {location}, {hazard}.",
    "{location} has {adj} potholes. {vehicle_issue}",
    "Deep road damage and broken asphalt near {location}. {impact}",
    "{adj} road condition on {location}, multiple potholes {action_needed}.",
    "Vehicle got damaged because of a {adj} pothole on {location}. {impact}",
    "Road surface has completely caved in near {location}. {hazard}",
    "Encountered {adj} trench across {location}. Can barely pass through.",
    "Bikers are falling down due to {adj} potholes near {location}. {accident_warning}",
    "Tar has washed away leaving {adj} holes on {location}. {action_needed}",
    "Huge trench and crater formation on {location}. {vehicle_issue}",
    "Very deep pothole, nearly caused an accident on {location}. {impact}",
    "Road is completely broken near {location}. Needs urgent repair.",
    "Multiple growing potholes on {location}. Worsening every day.",
    "Two wheelers are slipping on {location} because of damaged road and gravel.",
]

GARBAGE_TEMPLATES = [
    "{adj} garbage pile overflowing on {location}. {stench_issue}",
    "Waste has not been collected for {duration} near {location}. {health_hazard}",
    "Illegal dumping of {trash_type} on {location}. {stench_issue}",
    "Overflowing trash bin on {location}, {animal_issue}.",
    "Piles of rotting garbage dumped near {location}. {health_hazard}",
    "No sanitary worker has visited {location} for {duration}. Trash everywhere.",
    "Debris, plastic waste and rotten food dumped on {location}. {stench_issue}",
    "Garbage bin is broken and waste is spilling all over {location}. {animal_issue}",
    "Severely foul smell from trash dump on {location}. It is a health hazard.",
    "Roadside garbage accumulation near {location}. Breeding ground for mosquitoes.",
    "Commercial waste and rubbish piling up outside {location}. Needs clearing.",
    "Municipal truck has not cleared the garbage on {location} for {duration}.",
    "Stray animals scattering open garbage across {location}. Highly unhygienic.",
    "Massive pile of solid waste dumped by the roadside near {location}.",
    "Rotting organic waste creating terrible smell on {location}. Please clean urgently.",
]

WATERLOGGING_TEMPLATES = [
    "{adj} waterlogging on {location} after rain. {water_impact}",
    "Drainage is completely blocked near {location}. {water_depth}",
    "Knee-deep water stagnation on {location}. {traffic_issue}",
    "Sewage water overflowing from drain onto {location}. {health_hazard}",
    "Rainwater has flooded {location}, {water_impact}.",
    "Stormwater drain choked on {location}, water entering shops and homes.",
    "Severe flooding on {location}, cars are stalled and unable to pass.",
    "Standing water for {duration} near {location}. No drainage outlet.",
    "Water accumulated up to two feet on {location}. {traffic_issue}",
    "Clogged sewer causing dirty water to back up on {location}. {stench_issue}",
    "Entire stretch of {location} is submerged in water. Road is inaccessible.",
    "Slow drainage on {location} leads to water ponding every time it rains.",
    "Drain overflow near {location} creating mini lake on the street.",
    "Pedestrians cannot walk on {location} due to deep stagnant rainwater.",
    "Dangerous open drain overflowing onto the road at {location}.",
]

STREETLIGHT_TEMPLATES = [
    "Streetlight on {location} is {fault_type}. {darkness_impact}",
    "No street lights functioning on {location} for {duration}. Pitch dark at night.",
    "Lamp post on {location} has been {fault_type}. {safety_concern}",
    "Dark street on {location} due to broken streetlight. Very accident-prone.",
    "All lights along {location} are out. Women and seniors feel unsafe walking.",
    "Streetlight fixture flickering continuously on {location}. Needs replacement.",
    "Bulb burnt out on pole number near {location}. Street is completely dark.",
    "Street light pole leaning dangerously near {location}. Might fall down.",
    "Defective streetlights on {location} creating safety risk for commuters.",
    "No illumination on {location} after 7 PM. Multiple theft incidents reported.",
    "Wires exposed on streetlight pole at {location}. Severe shock hazard.",
    "Complete blackout on {location} stretch for past {duration}.",
    "Street light turns off intermittently on {location}. Road is accident-prone.",
    "Dark alley near {location} because pole light is dead. Please fix urgently.",
    "Lamppost light not working on {location}, unsafe for pedestrians.",
]

# Vocabulary components
LOCATIONS = [
    "Main Street", "Ring Road near Metro Station", "Sector 4 Market", "Park Avenue",
    "Bus Stand Road", "Railway Station Road", "Civil Hospital Gate", "School Lane",
    "Outer Ring Road flyover", "Service road near block C", "Connaught Circle",
    "South Extension", "Mall Road", "Industrial Area Phase 2", "Green Park Colony",
    "Nehru Place crossing", "MG Road junction", "Subhash Nagar main market",
    "Vikas Marg near bank", "Tilak Road opposite community center",
    "Ashok Vihar phase 1", "Dwarka Sector 10 crossing", "Rohini Sector 7 corner",
    "Lajpat Nagar central market", "Janakpuri district center road",
]

SEVERITY_PREFIXES = ["Deep", "Massive", "Dangerous", "Severe", "Growing", "Critical", "Huge"]
ADJECTIVES = ["huge", "deep", "hazardous", "massive", "terrible", "unattended", "giant", "worsening"]
IMPACTS = [
    "Cars are getting scratches and punctured tires",
    "Vehicles are swerving into oncoming traffic to avoid it",
    "Caused severe traffic jam during peak rush hour",
    "Bikers are at serious risk of fatal accidents",
    "Two-wheelers losing balance and skidding",
    "Causing vehicle underbody damage",
]
HAZARDS = [
    "an accident waiting to happen",
    "very dangerous especially in the dark",
    "causing severe traffic delays",
    "poses life threat to motorbikers",
]
VEHICLE_ISSUES = [
    "Suspension broke on a car yesterday",
    "Can easily break axles of smaller vehicles",
    "Tires getting blown out",
    "Auto rickshaws almost overturning",
]
ACTION_NEEDED = [
    "Needs urgent patch work",
    "Requires immediate road repair",
    "Please send municipal road crew",
    "Immediate asphalt filling required",
]
ACCIDENT_WARNINGS = [
    "Accident-prone zone, needs urgent barricading",
    "Already caused two bike falls this morning",
    "Pedestrians and cyclists in severe danger",
]

STENCH_ISSUES = [
    "The foul smell is unbearable for residents",
    "Terrible stench spreading across the entire neighborhood",
    "Residents cannot open their windows due to the rotten smell",
    "Unbearable foul odor spreading everywhere",
]
HEALTH_HAZARDS = [
    "Severe health hazard for young children and elderly",
    "Risk of dengue, cholera, and bacterial infection spreading",
    "Major public hygiene and sanitation crisis",
    "Health risk with flies and insects swarming all over",
]
ANIMAL_ISSUES = [
    "Cows and stray dogs are tearing up bags and spreading garbage",
    "Pigs and stray dogs feeding on rotten waste",
    "Animals scattering litter across both road lanes",
]
TRASH_TYPES = ["household garbage", "construction debris", "commercial trash", "plastic bags", "food waste"]
DURATIONS = ["two days", "four days", "over a week", "more than two weeks", "several days", "past ten days"]

WATER_IMPACTS = [
    "Water has entered ground floor homes and residential basements",
    "Water stagnating inside commercial shops causing merchandise loss",
    "Pedestrians are forced to wade through dirty knee-deep sewer water",
    "Traffic completely halted as road is impassable",
]
WATER_DEPTHS = ["water level is knee-deep", "standing water is 2 feet high", "water depth reaches calf height"]
TRAFFIC_ISSUES = [
    "Buses and cars are stuck in submerged water",
    "Two-wheelers are getting water in their silencers and stalling",
    "Long traffic gridlock stretching over a kilometer",
]

FAULT_TYPES = [
    "not working", "dead", "flickering continuously", "broken",
    "sparking and turned off", "damaged", "blown out",
]
DARKNESS_IMPACTS = [
    "Total darkness making it impossible to see the road",
    "Pitch black conditions at night causing security concerns",
    "Street is completely dark, creating danger for pedestrians",
    "Dark stretch creating major fear of robbery and accidents",
]
SAFETY_CONCERNS = [
    "Women and children feel extremely unsafe walking after dark",
    "Severe safety threat, anti-social elements gathering in the dark",
    "High probability of pedestrian collisions with speeding vehicles",
]


def generate_samples(templates, category, count=200):
    samples = []
    seen = set()

    while len(samples) < count:
        tmpl = random.choice(templates)
        text = tmpl.format(
            location=random.choice(LOCATIONS),
            severity_prefix=random.choice(SEVERITY_PREFIXES),
            adj=random.choice(ADJECTIVES),
            impact=random.choice(IMPACTS),
            hazard=random.choice(HAZARDS),
            vehicle_issue=random.choice(VEHICLE_ISSUES),
            action_needed=random.choice(ACTION_NEEDED),
            accident_warning=random.choice(ACCIDENT_WARNINGS),
            stench_issue=random.choice(STENCH_ISSUES),
            health_hazard=random.choice(HEALTH_HAZARDS),
            animal_issue=random.choice(ANIMAL_ISSUES),
            trash_type=random.choice(TRASH_TYPES),
            duration=random.choice(DURATIONS),
            water_impact=random.choice(WATER_IMPACTS),
            water_depth=random.choice(WATER_DEPTHS),
            traffic_issue=random.choice(TRAFFIC_ISSUES),
            fault_type=random.choice(FAULT_TYPES),
            darkness_impact=random.choice(DARKNESS_IMPACTS),
            safety_concern=random.choice(SAFETY_CONCERNS),
        )
        # Randomly apply mild typo / case variations in ~10% of samples for natural robustness
        if random.random() < 0.10:
            text = text.lower()

        if text not in seen:
            seen.add(text)
            samples.append({"text": text, "category": category})

    return samples


def main():
    print("Generating civic complaints text dataset...")

    potholes = generate_samples(POTHOLE_TEMPLATES, "Potholes / Damaged Roads", count=200)
    garbage = generate_samples(GARBAGE_TEMPLATES, "Garbage Accumulation", count=200)
    waterlogging = generate_samples(WATERLOGGING_TEMPLATES, "Waterlogging / Drainage Problems", count=200)
    streetlight = generate_samples(STREETLIGHT_TEMPLATES, "Streetlight Faults", count=200)

    all_data = potholes + garbage + waterlogging + streetlight
    random.shuffle(all_data)

    df = pd.DataFrame(all_data)

    out_dir = Path(__file__).resolve().parent.parent / "data" / "text"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "complaints_dataset.csv"
    df.to_csv(out_file, index=False)

    print(f"Dataset successfully created at: {out_file}")
    print(f"Total samples: {len(df)}")
    print(df["category"].value_counts())


if __name__ == "__main__":
    main()
