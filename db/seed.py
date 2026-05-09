"""Seed data for SQLite fallback mode.

100+ real lakes across WI, MN, IL, IA, MO with approximate coordinates,
acreages, depth, and species. Stocking events are generated relative to
"now" so the fishing-score recency buckets are exercised.
"""
from __future__ import annotations

import json
import random
import time
from typing import Any

import aiosqlite

# A curated list of real lakes. lat/lng are approximate centroids.
SEED_LAKES: list[dict[str, Any]] = [
    # ---------------- Wisconsin ----------------
    {"id": "lake-001", "name": "Lake Winnebago", "state": "WI", "county": "Winnebago", "lat": 44.00, "lng": -88.40, "acres": 137708, "max_depth_ft": 21, "species": ["walleye", "perch", "white_bass", "sturgeon"], "facilities": ["boat_ramp", "marina", "fish_cleaning"]},
    {"id": "lake-002", "name": "Devil's Lake", "state": "WI", "county": "Sauk", "lat": 43.42, "lng": -89.73, "acres": 360, "max_depth_ft": 47, "species": ["bass", "bluegill", "trout"], "facilities": ["boat_ramp", "campground"]},
    {"id": "lake-003", "name": "Lake Mendota", "state": "WI", "county": "Dane", "lat": 43.10, "lng": -89.42, "acres": 9847, "max_depth_ft": 83, "species": ["walleye", "musky", "bass", "perch"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-004", "name": "Lake Monona", "state": "WI", "county": "Dane", "lat": 43.06, "lng": -89.36, "acres": 3274, "max_depth_ft": 74, "species": ["walleye", "bass", "perch"], "facilities": ["boat_ramp"]},
    {"id": "lake-005", "name": "Lake Geneva", "state": "WI", "county": "Walworth", "lat": 42.59, "lng": -88.43, "acres": 5400, "max_depth_ft": 144, "species": ["bass", "trout", "pike"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-006", "name": "Big Green Lake", "state": "WI", "county": "Green Lake", "lat": 43.81, "lng": -88.97, "acres": 7346, "max_depth_ft": 236, "species": ["trout", "walleye", "bass"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-007", "name": "Castle Rock Lake", "state": "WI", "county": "Adams", "lat": 44.00, "lng": -89.96, "acres": 16640, "max_depth_ft": 34, "species": ["walleye", "musky", "panfish"], "facilities": ["boat_ramp", "campground"]},
    {"id": "lake-008", "name": "Petenwell Lake", "state": "WI", "county": "Adams", "lat": 44.13, "lng": -90.00, "acres": 23040, "max_depth_ft": 44, "species": ["walleye", "musky", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-009", "name": "Lake Wissota", "state": "WI", "county": "Chippewa", "lat": 44.99, "lng": -91.30, "acres": 6300, "max_depth_ft": 67, "species": ["walleye", "musky", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-010", "name": "Chippewa Flowage", "state": "WI", "county": "Sawyer", "lat": 45.91, "lng": -91.16, "acres": 15300, "max_depth_ft": 92, "species": ["musky", "walleye", "crappie"], "facilities": ["boat_ramp", "campground"]},
    {"id": "lake-011", "name": "Trout Lake", "state": "WI", "county": "Vilas", "lat": 46.03, "lng": -89.67, "acres": 3816, "max_depth_ft": 117, "species": ["trout", "walleye", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-012", "name": "Lake Tomahawk", "state": "WI", "county": "Oneida", "lat": 45.81, "lng": -89.71, "acres": 3392, "max_depth_ft": 81, "species": ["walleye", "musky", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-013", "name": "Pewaukee Lake", "state": "WI", "county": "Waukesha", "lat": 43.08, "lng": -88.27, "acres": 2493, "max_depth_ft": 45, "species": ["bass", "walleye", "panfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-014", "name": "Okauchee Lake", "state": "WI", "county": "Waukesha", "lat": 43.13, "lng": -88.43, "acres": 1210, "max_depth_ft": 90, "species": ["bass", "walleye"], "facilities": ["boat_ramp"]},
    {"id": "lake-015", "name": "Lake DuBay", "state": "WI", "county": "Marathon", "lat": 44.65, "lng": -89.69, "acres": 6830, "max_depth_ft": 35, "species": ["walleye", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-016", "name": "Lake Wisconsin", "state": "WI", "county": "Columbia", "lat": 43.30, "lng": -89.71, "acres": 9000, "max_depth_ft": 45, "species": ["walleye", "musky", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-017", "name": "Eagle Lake", "state": "WI", "county": "Racine", "lat": 42.78, "lng": -88.21, "acres": 519, "max_depth_ft": 65, "species": ["bass", "panfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-018", "name": "Beaver Dam Lake", "state": "WI", "county": "Dodge", "lat": 43.49, "lng": -88.83, "acres": 6710, "max_depth_ft": 14, "species": ["walleye", "panfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-019", "name": "Long Lake", "state": "WI", "county": "Washburn", "lat": 45.79, "lng": -91.81, "acres": 3290, "max_depth_ft": 72, "species": ["bass", "walleye", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-020", "name": "Cedar Lake", "state": "WI", "county": "Washington", "lat": 43.34, "lng": -88.20, "acres": 932, "max_depth_ft": 105, "species": ["bass", "panfish"], "facilities": ["boat_ramp"]},

    # ---------------- Minnesota ----------------
    {"id": "lake-021", "name": "Lake Minnetonka", "state": "MN", "county": "Hennepin", "lat": 44.93, "lng": -93.61, "acres": 14004, "max_depth_ft": 113, "species": ["bass", "walleye", "pike", "musky"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-022", "name": "Mille Lacs Lake", "state": "MN", "county": "Mille Lacs", "lat": 46.24, "lng": -93.65, "acres": 132516, "max_depth_ft": 42, "species": ["walleye", "smallmouth_bass", "musky", "perch"], "facilities": ["boat_ramp", "marina", "campground"]},
    {"id": "lake-023", "name": "Leech Lake", "state": "MN", "county": "Cass", "lat": 47.14, "lng": -94.40, "acres": 111527, "max_depth_ft": 156, "species": ["walleye", "musky", "perch", "bass"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-024", "name": "Lake of the Woods", "state": "MN", "county": "Lake of the Woods", "lat": 49.27, "lng": -94.83, "acres": 950000, "max_depth_ft": 210, "species": ["walleye", "sauger", "musky", "northern_pike"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-025", "name": "Red Lake", "state": "MN", "county": "Beltrami", "lat": 48.06, "lng": -94.83, "acres": 288800, "max_depth_ft": 35, "species": ["walleye", "northern_pike", "perch"], "facilities": ["boat_ramp"]},
    {"id": "lake-026", "name": "Lake Vermilion", "state": "MN", "county": "St. Louis", "lat": 47.88, "lng": -92.42, "acres": 39271, "max_depth_ft": 76, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-027", "name": "Cass Lake", "state": "MN", "county": "Cass", "lat": 47.39, "lng": -94.61, "acres": 15596, "max_depth_ft": 120, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-028", "name": "Big Stone Lake", "state": "MN", "county": "Big Stone", "lat": 45.41, "lng": -96.55, "acres": 12610, "max_depth_ft": 16, "species": ["walleye", "bass", "panfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-029", "name": "Gull Lake", "state": "MN", "county": "Cass", "lat": 46.43, "lng": -94.36, "acres": 9418, "max_depth_ft": 80, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-030", "name": "Lake Minnewaska", "state": "MN", "county": "Pope", "lat": 45.62, "lng": -95.45, "acres": 7110, "max_depth_ft": 35, "species": ["walleye", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-031", "name": "Lake Bemidji", "state": "MN", "county": "Beltrami", "lat": 47.51, "lng": -94.85, "acres": 6420, "max_depth_ft": 76, "species": ["walleye", "musky", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-032", "name": "Otter Tail Lake", "state": "MN", "county": "Otter Tail", "lat": 46.42, "lng": -95.65, "acres": 13725, "max_depth_ft": 120, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-033", "name": "Pelican Lake", "state": "MN", "county": "Otter Tail", "lat": 46.57, "lng": -95.92, "acres": 11069, "max_depth_ft": 104, "species": ["walleye", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-034", "name": "Lake Winnibigoshish", "state": "MN", "county": "Itasca", "lat": 47.43, "lng": -94.23, "acres": 56544, "max_depth_ft": 70, "species": ["walleye", "perch", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-035", "name": "Big Sandy Lake", "state": "MN", "county": "Aitkin", "lat": 46.74, "lng": -93.30, "acres": 7000, "max_depth_ft": 80, "species": ["walleye", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-036", "name": "White Bear Lake", "state": "MN", "county": "Ramsey", "lat": 45.07, "lng": -93.00, "acres": 2427, "max_depth_ft": 83, "species": ["bass", "panfish", "walleye"], "facilities": ["boat_ramp"]},
    {"id": "lake-037", "name": "Forest Lake", "state": "MN", "county": "Washington", "lat": 45.27, "lng": -92.96, "acres": 2251, "max_depth_ft": 35, "species": ["walleye", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-038", "name": "Medicine Lake", "state": "MN", "county": "Hennepin", "lat": 45.02, "lng": -93.41, "acres": 886, "max_depth_ft": 49, "species": ["bass", "panfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-039", "name": "Lake Phalen", "state": "MN", "county": "Ramsey", "lat": 44.99, "lng": -93.07, "acres": 198, "max_depth_ft": 91, "species": ["bass", "trout", "panfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-040", "name": "Lake Nokomis", "state": "MN", "county": "Hennepin", "lat": 44.91, "lng": -93.24, "acres": 204, "max_depth_ft": 33, "species": ["bass", "panfish"], "facilities": ["boat_ramp"]},

    # ---------------- Illinois ----------------
    {"id": "lake-041", "name": "Shabbona Lake", "state": "IL", "county": "DeKalb", "lat": 41.74, "lng": -88.85, "acres": 319, "max_depth_ft": 28, "species": ["trout", "bass", "catfish", "musky"], "facilities": ["boat_ramp", "campground"]},
    {"id": "lake-042", "name": "Carlyle Lake", "state": "IL", "county": "Clinton", "lat": 38.65, "lng": -89.36, "acres": 26000, "max_depth_ft": 35, "species": ["walleye", "white_bass", "catfish", "crappie"], "facilities": ["boat_ramp", "marina", "campground"]},
    {"id": "lake-043", "name": "Rend Lake", "state": "IL", "county": "Franklin", "lat": 38.04, "lng": -88.95, "acres": 18900, "max_depth_ft": 35, "species": ["crappie", "bass", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-044", "name": "Crab Orchard Lake", "state": "IL", "county": "Williamson", "lat": 37.71, "lng": -89.06, "acres": 6965, "max_depth_ft": 40, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-045", "name": "Lake Shelbyville", "state": "IL", "county": "Shelby", "lat": 39.43, "lng": -88.78, "acres": 11100, "max_depth_ft": 65, "species": ["walleye", "bass", "muskie", "crappie"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-046", "name": "Lake Springfield", "state": "IL", "county": "Sangamon", "lat": 39.71, "lng": -89.61, "acres": 4260, "max_depth_ft": 30, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-047", "name": "Lake Decatur", "state": "IL", "county": "Macon", "lat": 39.85, "lng": -88.91, "acres": 2800, "max_depth_ft": 25, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-048", "name": "Lake Bloomington", "state": "IL", "county": "McLean", "lat": 40.62, "lng": -88.91, "acres": 635, "max_depth_ft": 30, "species": ["bass", "musky", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-049", "name": "Evergreen Lake", "state": "IL", "county": "McLean", "lat": 40.59, "lng": -88.99, "acres": 925, "max_depth_ft": 56, "species": ["bass", "musky", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-050", "name": "Powerton Lake", "state": "IL", "county": "Tazewell", "lat": 40.55, "lng": -89.66, "acres": 1400, "max_depth_ft": 30, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-051", "name": "Lake Sangchris", "state": "IL", "county": "Christian", "lat": 39.62, "lng": -89.49, "acres": 2165, "max_depth_ft": 32, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-052", "name": "Lake Vermilion (IL)", "state": "IL", "county": "Vermilion", "lat": 40.18, "lng": -87.74, "acres": 900, "max_depth_ft": 30, "species": ["bass", "crappie", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-053", "name": "Lou Yaeger Lake", "state": "IL", "county": "Montgomery", "lat": 39.21, "lng": -89.65, "acres": 1400, "max_depth_ft": 28, "species": ["bass", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-054", "name": "Heidecke Lake", "state": "IL", "county": "Grundy", "lat": 41.30, "lng": -88.31, "acres": 1955, "max_depth_ft": 38, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-055", "name": "Mazonia Lake", "state": "IL", "county": "Grundy", "lat": 41.25, "lng": -88.21, "acres": 2400, "max_depth_ft": 25, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-056", "name": "Banner Marsh", "state": "IL", "county": "Fulton", "lat": 40.59, "lng": -89.93, "acres": 2000, "max_depth_ft": 20, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-057", "name": "Goose Lake", "state": "IL", "county": "Grundy", "lat": 41.32, "lng": -88.32, "acres": 360, "max_depth_ft": 12, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-058", "name": "Clinton Lake", "state": "IL", "county": "DeWitt", "lat": 40.16, "lng": -88.79, "acres": 4900, "max_depth_ft": 32, "species": ["walleye", "bass", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-059", "name": "Kinkaid Lake", "state": "IL", "county": "Jackson", "lat": 37.77, "lng": -89.41, "acres": 2750, "max_depth_ft": 80, "species": ["bass", "crappie", "musky"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-060", "name": "Lake Calumet", "state": "IL", "county": "Cook", "lat": 41.69, "lng": -87.59, "acres": 800, "max_depth_ft": 30, "species": ["bass", "perch"], "facilities": ["boat_ramp"]},

    # ---------------- Iowa ----------------
    {"id": "lake-061", "name": "Lake Red Rock", "state": "IA", "county": "Marion", "lat": 41.39, "lng": -92.99, "acres": 19000, "max_depth_ft": 48, "species": ["walleye", "crappie", "bass", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-062", "name": "Coralville Lake", "state": "IA", "county": "Johnson", "lat": 41.78, "lng": -91.55, "acres": 4900, "max_depth_ft": 50, "species": ["walleye", "crappie", "bass"], "facilities": ["boat_ramp", "campground"]},
    {"id": "lake-063", "name": "Saylorville Lake", "state": "IA", "county": "Polk", "lat": 41.71, "lng": -93.67, "acres": 5950, "max_depth_ft": 75, "species": ["walleye", "white_bass", "crappie"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-064", "name": "Rathbun Lake", "state": "IA", "county": "Appanoose", "lat": 40.83, "lng": -92.91, "acres": 11000, "max_depth_ft": 50, "species": ["walleye", "bass", "crappie"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-065", "name": "Lake Macbride", "state": "IA", "county": "Johnson", "lat": 41.79, "lng": -91.55, "acres": 940, "max_depth_ft": 60, "species": ["walleye", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-066", "name": "Big Creek Lake", "state": "IA", "county": "Polk", "lat": 41.79, "lng": -93.74, "acres": 866, "max_depth_ft": 55, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp"]},
    {"id": "lake-067", "name": "Clear Lake", "state": "IA", "county": "Cerro Gordo", "lat": 43.13, "lng": -93.40, "acres": 3684, "max_depth_ft": 19, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-068", "name": "Storm Lake", "state": "IA", "county": "Buena Vista", "lat": 42.63, "lng": -95.20, "acres": 3097, "max_depth_ft": 14, "species": ["walleye", "bass", "panfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-069", "name": "Lake Anita", "state": "IA", "county": "Cass", "lat": 41.42, "lng": -94.74, "acres": 171, "max_depth_ft": 28, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-070", "name": "West Okoboji Lake", "state": "IA", "county": "Dickinson", "lat": 43.39, "lng": -95.18, "acres": 3939, "max_depth_ft": 134, "species": ["walleye", "bass", "musky", "perch"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-071", "name": "East Okoboji Lake", "state": "IA", "county": "Dickinson", "lat": 43.39, "lng": -95.13, "acres": 1875, "max_depth_ft": 24, "species": ["walleye", "bass"], "facilities": ["boat_ramp"]},
    {"id": "lake-072", "name": "Spirit Lake", "state": "IA", "county": "Dickinson", "lat": 43.45, "lng": -95.10, "acres": 5684, "max_depth_ft": 24, "species": ["walleye", "bass", "musky"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-073", "name": "Lake Manawa", "state": "IA", "county": "Pottawattamie", "lat": 41.21, "lng": -95.85, "acres": 660, "max_depth_ft": 22, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-074", "name": "Lake Ahquabi", "state": "IA", "county": "Warren", "lat": 41.27, "lng": -93.59, "acres": 115, "max_depth_ft": 25, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-075", "name": "Hickory Grove Lake", "state": "IA", "county": "Story", "lat": 42.05, "lng": -93.30, "acres": 100, "max_depth_ft": 34, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-076", "name": "Don Williams Lake", "state": "IA", "county": "Boone", "lat": 42.13, "lng": -94.04, "acres": 150, "max_depth_ft": 35, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-077", "name": "Lake Wapello", "state": "IA", "county": "Davis", "lat": 40.83, "lng": -92.59, "acres": 289, "max_depth_ft": 35, "species": ["bass", "crappie", "trout"], "facilities": ["boat_ramp", "campground"]},
    {"id": "lake-078", "name": "Twelve Mile Lake", "state": "IA", "county": "Union", "lat": 41.07, "lng": -94.30, "acres": 635, "max_depth_ft": 32, "species": ["bass", "walleye"], "facilities": ["boat_ramp"]},
    {"id": "lake-079", "name": "Lake of Three Fires", "state": "IA", "county": "Taylor", "lat": 40.79, "lng": -94.69, "acres": 97, "max_depth_ft": 30, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-080", "name": "Beeds Lake", "state": "IA", "county": "Franklin", "lat": 42.78, "lng": -93.27, "acres": 99, "max_depth_ft": 22, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},

    # ---------------- Missouri ----------------
    {"id": "lake-081", "name": "Lake of the Ozarks", "state": "MO", "county": "Camden", "lat": 38.20, "lng": -92.78, "acres": 54000, "max_depth_ft": 130, "species": ["bass", "crappie", "catfish", "walleye"], "facilities": ["boat_ramp", "marina", "campground"]},
    {"id": "lake-082", "name": "Truman Lake", "state": "MO", "county": "Benton", "lat": 38.27, "lng": -93.42, "acres": 55600, "max_depth_ft": 80, "species": ["crappie", "bass", "walleye", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-083", "name": "Bull Shoals Lake", "state": "MO", "county": "Taney", "lat": 36.52, "lng": -92.82, "acres": 45440, "max_depth_ft": 210, "species": ["bass", "trout", "crappie"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-084", "name": "Table Rock Lake", "state": "MO", "county": "Stone", "lat": 36.59, "lng": -93.31, "acres": 43100, "max_depth_ft": 220, "species": ["bass", "crappie", "trout"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-085", "name": "Stockton Lake", "state": "MO", "county": "Cedar", "lat": 37.66, "lng": -93.74, "acres": 24900, "max_depth_ft": 165, "species": ["walleye", "bass", "crappie"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-086", "name": "Pomme de Terre Lake", "state": "MO", "county": "Hickory", "lat": 37.91, "lng": -93.32, "acres": 7820, "max_depth_ft": 145, "species": ["musky", "bass", "crappie"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-087", "name": "Mark Twain Lake", "state": "MO", "county": "Monroe", "lat": 39.55, "lng": -91.62, "acres": 18600, "max_depth_ft": 80, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-088", "name": "Smithville Lake", "state": "MO", "county": "Clay", "lat": 39.43, "lng": -94.59, "acres": 7200, "max_depth_ft": 60, "species": ["walleye", "bass", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-089", "name": "Longview Lake", "state": "MO", "county": "Jackson", "lat": 38.91, "lng": -94.50, "acres": 930, "max_depth_ft": 33, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-090", "name": "Blue Springs Lake", "state": "MO", "county": "Jackson", "lat": 39.04, "lng": -94.32, "acres": 720, "max_depth_ft": 60, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-091", "name": "Lake Taneycomo", "state": "MO", "county": "Taney", "lat": 36.65, "lng": -93.22, "acres": 2080, "max_depth_ft": 50, "species": ["trout"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-092", "name": "Norfork Lake", "state": "MO", "county": "Ozark", "lat": 36.50, "lng": -92.30, "acres": 22000, "max_depth_ft": 177, "species": ["bass", "trout", "crappie"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-093", "name": "Wappapello Lake", "state": "MO", "county": "Wayne", "lat": 36.93, "lng": -90.31, "acres": 8400, "max_depth_ft": 56, "species": ["crappie", "bass", "catfish"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-094", "name": "Lake Jacomo", "state": "MO", "county": "Jackson", "lat": 38.94, "lng": -94.31, "acres": 970, "max_depth_ft": 40, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-095", "name": "Lake Springfield (MO)", "state": "MO", "county": "Greene", "lat": 37.13, "lng": -93.21, "acres": 320, "max_depth_ft": 30, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-096", "name": "Watkins Mill Lake", "state": "MO", "county": "Clay", "lat": 39.39, "lng": -94.25, "acres": 100, "max_depth_ft": 20, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-097", "name": "Thomas Hill Reservoir", "state": "MO", "county": "Randolph", "lat": 39.55, "lng": -92.65, "acres": 4950, "max_depth_ft": 50, "species": ["bass", "crappie", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-098", "name": "Long Branch Lake", "state": "MO", "county": "Macon", "lat": 39.78, "lng": -92.51, "acres": 2430, "max_depth_ft": 50, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-099", "name": "Forest Lake (MO)", "state": "MO", "county": "Adair", "lat": 40.18, "lng": -92.63, "acres": 575, "max_depth_ft": 35, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
    {"id": "lake-100", "name": "Lake Wauconda", "state": "MO", "county": "Lewis", "lat": 40.13, "lng": -91.85, "acres": 200, "max_depth_ft": 28, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},

    # ---------------- Extra (cushion past 100) ----------------
    {"id": "lake-101", "name": "Lake Michigan (Milwaukee shore)", "state": "WI", "county": "Milwaukee", "lat": 43.04, "lng": -87.91, "acres": 22300000, "max_depth_ft": 923, "species": ["salmon", "trout", "perch"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-102", "name": "Lake Pepin", "state": "WI", "county": "Pierce", "lat": 44.50, "lng": -92.20, "acres": 28150, "max_depth_ft": 60, "species": ["walleye", "sauger", "white_bass"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-103", "name": "Lake Superior (Duluth shore)", "state": "MN", "county": "St. Louis", "lat": 46.78, "lng": -92.10, "acres": 20300000, "max_depth_ft": 1333, "species": ["lake_trout", "salmon", "smelt"], "facilities": ["boat_ramp", "marina"]},
    {"id": "lake-104", "name": "Spring Lake", "state": "IL", "county": "Tazewell", "lat": 40.50, "lng": -89.74, "acres": 2050, "max_depth_ft": 12, "species": ["bass", "catfish"], "facilities": ["boat_ramp"]},
    {"id": "lake-105", "name": "Lake Icaria", "state": "IA", "county": "Adams", "lat": 41.04, "lng": -94.68, "acres": 660, "max_depth_ft": 50, "species": ["bass", "walleye"], "facilities": ["boat_ramp"]},
    {"id": "lake-106", "name": "Lake Ozark Tributary", "state": "MO", "county": "Miller", "lat": 38.20, "lng": -92.62, "acres": 150, "max_depth_ft": 30, "species": ["bass", "crappie"], "facilities": ["boat_ramp"]},
]


# Stocking templates: per-lake recent + older events.
# `date_offset_days` is days BEFORE "now" the event happened.
SEED_STOCKINGS_TEMPLATE: list[dict[str, Any]] = [
    # Recent (≤30 days) — these maximize recency bonus
    {"lake_id": "lake-001", "species": "walleye", "count": 50000, "date_offset_days": 14},
    {"lake_id": "lake-001", "species": "perch", "count": 12000, "date_offset_days": 28},
    {"lake_id": "lake-002", "species": "bass", "count": 2000, "date_offset_days": 22},
    {"lake_id": "lake-003", "species": "walleye", "count": 8000, "date_offset_days": 9},
    {"lake_id": "lake-005", "species": "trout", "count": 5000, "date_offset_days": 7},
    {"lake_id": "lake-006", "species": "trout", "count": 4500, "date_offset_days": 12},
    {"lake_id": "lake-021", "species": "musky", "count": 1500, "date_offset_days": 18},
    {"lake_id": "lake-022", "species": "walleye", "count": 60000, "date_offset_days": 5},
    {"lake_id": "lake-023", "species": "walleye", "count": 40000, "date_offset_days": 11},
    {"lake_id": "lake-024", "species": "walleye", "count": 75000, "date_offset_days": 3},
    {"lake_id": "lake-041", "species": "trout", "count": 3500, "date_offset_days": 6},
    {"lake_id": "lake-042", "species": "white_bass", "count": 9000, "date_offset_days": 15},
    {"lake_id": "lake-045", "species": "walleye", "count": 6500, "date_offset_days": 21},
    {"lake_id": "lake-061", "species": "walleye", "count": 18000, "date_offset_days": 8},
    {"lake_id": "lake-067", "species": "walleye", "count": 12000, "date_offset_days": 17},
    {"lake_id": "lake-070", "species": "walleye", "count": 22000, "date_offset_days": 4},
    {"lake_id": "lake-072", "species": "walleye", "count": 25000, "date_offset_days": 10},
    {"lake_id": "lake-081", "species": "bass", "count": 4500, "date_offset_days": 13},
    {"lake_id": "lake-082", "species": "crappie", "count": 8000, "date_offset_days": 19},
    {"lake_id": "lake-085", "species": "walleye", "count": 11000, "date_offset_days": 25},
    {"lake_id": "lake-091", "species": "trout", "count": 16000, "date_offset_days": 6},

    # 31-90 day window (20 pt bucket)
    {"lake_id": "lake-002", "species": "bluegill", "count": 5000, "date_offset_days": 45},
    {"lake_id": "lake-007", "species": "walleye", "count": 12000, "date_offset_days": 60},
    {"lake_id": "lake-008", "species": "walleye", "count": 14000, "date_offset_days": 70},
    {"lake_id": "lake-009", "species": "musky", "count": 800, "date_offset_days": 55},
    {"lake_id": "lake-010", "species": "musky", "count": 700, "date_offset_days": 38},
    {"lake_id": "lake-011", "species": "trout", "count": 3000, "date_offset_days": 50},
    {"lake_id": "lake-026", "species": "walleye", "count": 18000, "date_offset_days": 75},
    {"lake_id": "lake-027", "species": "musky", "count": 600, "date_offset_days": 80},
    {"lake_id": "lake-029", "species": "walleye", "count": 11000, "date_offset_days": 40},
    {"lake_id": "lake-031", "species": "walleye", "count": 9000, "date_offset_days": 65},
    {"lake_id": "lake-034", "species": "perch", "count": 25000, "date_offset_days": 55},
    {"lake_id": "lake-043", "species": "crappie", "count": 14000, "date_offset_days": 35},
    {"lake_id": "lake-044", "species": "bass", "count": 3000, "date_offset_days": 88},
    {"lake_id": "lake-046", "species": "bass", "count": 2200, "date_offset_days": 50},
    {"lake_id": "lake-049", "species": "musky", "count": 400, "date_offset_days": 70},
    {"lake_id": "lake-058", "species": "walleye", "count": 8500, "date_offset_days": 85},
    {"lake_id": "lake-062", "species": "walleye", "count": 11000, "date_offset_days": 42},
    {"lake_id": "lake-063", "species": "walleye", "count": 13000, "date_offset_days": 65},
    {"lake_id": "lake-064", "species": "walleye", "count": 14000, "date_offset_days": 80},
    {"lake_id": "lake-066", "species": "musky", "count": 350, "date_offset_days": 45},
    {"lake_id": "lake-068", "species": "walleye", "count": 7500, "date_offset_days": 55},
    {"lake_id": "lake-083", "species": "trout", "count": 22000, "date_offset_days": 40},
    {"lake_id": "lake-084", "species": "bass", "count": 5500, "date_offset_days": 60},
    {"lake_id": "lake-086", "species": "musky", "count": 600, "date_offset_days": 75},
    {"lake_id": "lake-087", "species": "crappie", "count": 12000, "date_offset_days": 50},
    {"lake_id": "lake-088", "species": "walleye", "count": 7800, "date_offset_days": 88},

    # 91-180 day window (10 pts)
    {"lake_id": "lake-013", "species": "panfish", "count": 8000, "date_offset_days": 120},
    {"lake_id": "lake-016", "species": "walleye", "count": 9000, "date_offset_days": 150},
    {"lake_id": "lake-018", "species": "walleye", "count": 6500, "date_offset_days": 110},
    {"lake_id": "lake-028", "species": "walleye", "count": 13000, "date_offset_days": 135},
    {"lake_id": "lake-032", "species": "bass", "count": 4500, "date_offset_days": 175},
    {"lake_id": "lake-047", "species": "catfish", "count": 9500, "date_offset_days": 145},
    {"lake_id": "lake-051", "species": "bass", "count": 3000, "date_offset_days": 100},
    {"lake_id": "lake-054", "species": "walleye", "count": 5000, "date_offset_days": 160},
    {"lake_id": "lake-059", "species": "musky", "count": 200, "date_offset_days": 110},
    {"lake_id": "lake-065", "species": "walleye", "count": 6000, "date_offset_days": 130},
    {"lake_id": "lake-071", "species": "walleye", "count": 8000, "date_offset_days": 95},
    {"lake_id": "lake-073", "species": "bass", "count": 2200, "date_offset_days": 165},
    {"lake_id": "lake-077", "species": "trout", "count": 1800, "date_offset_days": 100},
    {"lake_id": "lake-089", "species": "bass", "count": 1900, "date_offset_days": 105},
    {"lake_id": "lake-092", "species": "trout", "count": 16000, "date_offset_days": 130},
    {"lake_id": "lake-093", "species": "crappie", "count": 8000, "date_offset_days": 170},
    {"lake_id": "lake-097", "species": "catfish", "count": 5500, "date_offset_days": 140},

    # >180 day stragglers (no recency bonus, but still feed species/freshness)
    {"lake_id": "lake-019", "species": "musky", "count": 250, "date_offset_days": 220},
    {"lake_id": "lake-035", "species": "walleye", "count": 6000, "date_offset_days": 250},
    {"lake_id": "lake-048", "species": "musky", "count": 200, "date_offset_days": 240},
    {"lake_id": "lake-074", "species": "bass", "count": 1500, "date_offset_days": 280},
    {"lake_id": "lake-101", "species": "salmon", "count": 100000, "date_offset_days": 200},
    {"lake_id": "lake-103", "species": "lake_trout", "count": 50000, "date_offset_days": 230},
]


async def seed_sqlite(db: aiosqlite.Connection) -> None:
    """Insert seed data into a fresh SQLite connection. Idempotent."""
    # Skip if already populated (re-init guard)
    async with db.execute("SELECT COUNT(*) FROM lakes") as cur:
        row = await cur.fetchone()
        if row and row[0] and row[0] > 0:
            return

    now = time.time()
    rng = random.Random(42)

    # Lakes
    for lake in SEED_LAKES:
        await db.execute(
            "INSERT OR REPLACE INTO lakes "
            "(id, name, state, county, lat, lng, acres, max_depth_ft, facilities) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                lake["id"],
                lake["name"],
                lake["state"],
                lake.get("county"),
                lake["lat"],
                lake["lng"],
                lake["acres"],
                lake.get("max_depth_ft"),
                json.dumps(lake.get("facilities", [])),
            ),
        )
        for sp in lake.get("species", []):
            await db.execute(
                "INSERT OR IGNORE INTO lake_species (lake_id, species) VALUES (?, ?)",
                (lake["id"], sp),
            )

    # Stockings — use template + add a few synthetic events for unmentioned lakes
    template = list(SEED_STOCKINGS_TEMPLATE)
    seen_lake_ids = {s["lake_id"] for s in template}
    for lake in SEED_LAKES:
        if lake["id"] not in seen_lake_ids and lake.get("species"):
            # one mid-recency event so most lakes have some history
            template.append(
                {
                    "lake_id": lake["id"],
                    "species": rng.choice(lake["species"]),
                    "count": rng.randint(500, 12000),
                    "date_offset_days": rng.randint(40, 180),
                }
            )

    for s in template:
        ts = now - (float(s["date_offset_days"]) * 86400.0)
        await db.execute(
            "INSERT INTO stockings (lake_id, species, count, stocking_date) "
            "VALUES (?, ?, ?, ?)",
            (s["lake_id"], s["species"], int(s["count"]), ts),
        )

    await db.commit()


def lake_count() -> int:
    return len(SEED_LAKES)


def stocking_event_count() -> int:
    template_count = len(SEED_STOCKINGS_TEMPLATE)
    seen = {s["lake_id"] for s in SEED_STOCKINGS_TEMPLATE}
    extra = sum(1 for l in SEED_LAKES if l["id"] not in seen and l.get("species"))
    return template_count + extra
