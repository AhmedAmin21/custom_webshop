/* ==========================================================================
   CNCLeaders Premium E-Commerce Application Controller
   ========================================================================== */

// --- 1. SEED INVENTORY (ERPNext Source of Truth) ---
const INITIAL_PRODUCTS = [
    {
        "name": "High-Speed 2.2kW Spindle Motor",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 350,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-01"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 2)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 360,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-02"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 3)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 365,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-03"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 4)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 370,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-04"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 5)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 375,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-05"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 6)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 380,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-06"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 7)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 385,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-07"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 8)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 390,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-08"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 9)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 395,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-09"
    },
    {
        "name": "High-Speed 2.2kW Spindle Motor (Variant 10)",
        "category": "spindles",
        "categoryName": "Spindle Systems",
        "brand": "CNCLeaders",
        "description": "Industrial grade air-cooled spindle motor featuring low-runout precision steel bearings. Engineered for high continuous loads in steel, aluminum, and heavy composite milling. ERPNext certified.",
        "price": 400,
        "image": "assets/images/cnc_spindle_motor.jpg",
        "stock": 12,
        "sold": 48,
        "specs": {
            "Power Rating": "2.2 kW",
            "Rated Velocity": "24,000 RPM",
            "Collet System": "ER20 (Included)",
            "Bearings Runout": "< 0.005 mm",
            "Input Voltage": "3-Phase 220V VFD"
        },
        "id": "CNC-SP-10"
    },
    {
        "name": "HGR20 Linear Guide Rail Set",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 120,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-01"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 2)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 130,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-02"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 3)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 135,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-03"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 4)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 140,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-04"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 5)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 145,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-05"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 6)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 150,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-06"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 7)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 155,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-07"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 8)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 160,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-08"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 9)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 165,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-09"
    },
    {
        "name": "HGR20 Linear Guide Rail Set (Variant 10)",
        "category": "guides",
        "categoryName": "Linear Guides",
        "brand": "NSK Precision",
        "description": "Ultra-precision HGR20 carbon steel profile rails featuring high load capacities and extreme rigidity. Includes recirculating ball slide carriages with dual scraper dust seals.",
        "price": 170,
        "image": "assets/images/linear_guide_rail.jpg",
        "stock": 25,
        "sold": 92,
        "specs": {
            "Rail Profile": "HGR20 Standard",
            "Total Length": "1000 mm (x2 Rails)",
            "Carriage Blocks": "4x HGH20CA Flanged",
            "Material Grade": "High-Hardness GCr15 Steel",
            "Tolerance Class": "H Class High Precision"
        },
        "id": "CNC-GR-10"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 45,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-01"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 2)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 55,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-02"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 3)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 60,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-03"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 4)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 65,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-04"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 5)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 70,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-05"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 6)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 75,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-06"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 7)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 80,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-07"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 8)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 85,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-08"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 9)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 90,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-09"
    },
    {
        "name": "Blue-Coated Carbide End Mill Kit (Variant 10)",
        "category": "tooling",
        "categoryName": "Solid Tooling",
        "brand": "Sandvik Coromant",
        "description": "AlTiN nano-blue coated solid micrograin carbide end mills. Offers superior oxidation resistance and high hardness for routing abrasive plastics, composites, and carbon fibers.",
        "price": 95,
        "image": "assets/images/carbide_end_mills.jpg",
        "stock": 150,
        "sold": 175,
        "specs": {
            "Flute Count": "4 Flutes Helical",
            "Shank Diameter": "6.0 mm (H6 Tolerance)",
            "Coating Compound": "AlTiN Silicon Nano-Blue",
            "Maximum Depth": "22.0 mm Cut Length",
            "Hardness Capacity": "Up to 55 HRC"
        },
        "id": "CNC-TL-10"
    },
    {
        "name": "4-Axis GRBL Offline Controller",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 85,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-01"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 2)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 95,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-02"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 3)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 100,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-03"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 4)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 105,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-04"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 5)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 110,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-05"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 6)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 115,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-06"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 7)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 120,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-07"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 8)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 125,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-08"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 9)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 130,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-09"
    },
    {
        "name": "4-Axis GRBL Offline Controller (Variant 10)",
        "category": "electronics",
        "categoryName": "Controllers & Drivers",
        "brand": "Delta Electronics",
        "description": "Offline standalone breakout motion board featuring dual optocoupler noise isolation and micro-stepper telemetry outputs. Eliminates PC crashes during long machining processes.",
        "price": 135,
        "image": "assets/images/cnc_controller_board.jpg",
        "stock": 8,
        "sold": 34,
        "specs": {
            "Control Channels": "4 Axis Step/Dir Outputs",
            "Offline Input": "MicroSD Slot & G-Code Parser",
            "Optoisolation": "High-Speed Optocouplers",
            "Supply Input": "12-24V DC Regulated",
            "Limits Interface": "6x Hardware Limit Ports"
        },
        "id": "CNC-CT-10"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 95,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-01"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 2)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 105,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-02"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 3)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 110,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-03"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 4)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 115,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-04"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 5)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 120,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-05"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 6)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 125,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-06"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 7)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 130,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-07"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 8)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 135,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-08"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 9)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 140,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-09"
    },
    {
        "name": "SFU1605 Precision Ball Screw Kit (Variant 10)",
        "category": "motion",
        "categoryName": "Linear Actuators",
        "brand": "NSK Precision",
        "description": "High-precision ball screw assembly. Delivers smooth mechanical efficiency with low friction coefficient and minimal backlash. Includes machined end supports and housing blocks.",
        "price": 145,
        "image": "assets/images/ball_screw_assembly.jpg",
        "stock": 18,
        "sold": 63,
        "specs": {
            "Model Designation": "SFU1605 Rolled Screws",
            "Lead Pitch": "5.0 mm Per Turn",
            "Screw Length": "800 mm Total Length",
            "Supports Included": "FK12 Fixed, FF12 Floating",
            "Axial Backlash": "< 0.010 mm"
        },
        "id": "CNC-BS-10"
    }
];

const INITIAL_SLIDES = [
    {
        eyebrow: "PRECISION CNC ENGINEERING",
        title: "Industrial Components built for micro-tolerance performance",
        subtitle: "Direct distributor of high-torque spindle systems, premium linear rails, high-resolution stepper systems, and carbide tooling. ERPNext Synced.",
        link: "#catalog",
        image: "assets/images/cnc_spindle_motor.jpg"
    },
    {
        eyebrow: "MOTION CONTROL TELEMETRY",
        title: "Linear Motion Guides & Precision Ball Screws",
        subtitle: "H Class GCr15 carbon steel rails with heavy duty flanged blocks. Low axial backlash SFU actuators.",
        link: "#catalog?category=guides",
        image: "assets/images/linear_guide_rail.jpg"
    },
    {
        eyebrow: "HARDENED ROTARY CUTTERS",
        title: "Solid Carbide Spiral End Mill Kits",
        subtitle: "AlTiN nano-blue coated 4-flute routing bits. Resists friction and high thermal loads up to 55 HRC.",
        link: "#catalog?category=tooling",
        image: "assets/images/carbide_end_mills.jpg"
    }
];

const CATEGORIES = {
    all: "All Components",
    spindles: "Spindles",
    guides: "Linear Guides",
    tooling: "Solid Tooling",
    electronics: "Electronics",
    motion: "Linear Actuators"
};

const CATEGORY_DESCRIPTIONS = {
    all: "Complete directory of certified industrial manufacturing parts.",
    spindles: "High-torque air and water-cooled motors for continuous industrial milling.",
    guides: "Precision-ground guide rails and blocks for ultra-smooth multi-axis motion.",
    tooling: "Premium tungsten carbide end mills designed for advanced material removal.",
    electronics: "Opto-isolated motion controllers and breakout boards for reliable signal routing.",
    motion: "High-accuracy ball screw assemblies for zero-backlash mechanical drives."
};

let state = { products: [], cart: [], orders: [], slides: [], activeView: "home", selectedProductId: null, selectedBrandFilter: "all", pendingReceiptFile: null, activeAdminTab: "analytics", theme: "light", lang: "ar", catalogViewMode: "grid" };

const TRANSLATIONS = {
    en: {
        nav_home: "Home", nav_catalog: "All Products", nav_orders: "Track Orders", nav_admin: "Admin Panel",
        home_shop_material: "Shop by Material", home_shop_material_sub: "Browse components by manufacturing material",
        material_wood: "Wood & MDF", material_acrylic: "Acrylic & Plastic", material_metal: "Aluminum & Metals",
        material_all: "View all categories", home_shop_category: "Shop by Category",
        home_shop_category_sub: "Swipe through certified high-precision parts by class",
        home_trending: "Trending Equipment", home_trending_sub: "Most demanded components based on active CNC machining workshop configurations",
        home_shop_brand: "Shop by Certified Brand", home_shop_brand_sub: "Genuine mechanical components from authorized industrial manufacturers",
        filter_search: "Search", filter_search_placeholder: "Search by model or spec...",
        filter_category: "Category", filter_stock: "Stock Status", filter_instock_only: "In Stock Only",
        filter_max_price: "Max Price ($)", filter_brand: "Brand", btn_reset_filters: "Reset Filters",
        catalog_sort: "Sort: ", sort_default: "Default Sync Order", sort_price_asc: "Price: Low to High",
        sort_price_desc: "Price: High to Low", sort_alpha: "A-Z Name", cart_selected: "Your Selected Hardware",
        cart_cost_structure: "Order Cost Structure", cart_subtotal: "Subtotal", cart_shipping: "Shipping (Simulated CNC Cargo)",
        cart_total: "Grand Total", cart_delivery: "Delivery & Shipping Address", cart_name: "Full Name / Company Name *",
        cart_name_placeholder: "e.g. John Doe, Machining LLC", cart_phone: "Contact Phone Number *",
        cart_phone_placeholder: "e.g. +1 555-0199", cart_address: "Shipping Address *",
        cart_address_placeholder: "Street address, unit, city, state, zip code...", cart_notes: "Machining Details / Delivery Instructions",
        cart_notes_placeholder: "Notes (e.g. loading dock hours, fork-lift requirements)", cart_proceed: "Proceed to checkout",
        payment_title: "Checkout", payment_subtitle: "To complete order processing and trigger ERPNext packaging, please wire the total amount and upload your receipt screenshot below.",
        payment_amount_label: "Amount Outstanding", payment_method: "Choose Payment Method",
        payment_upload_title: "Provide Payment Confirmation", payment_upload_text: "Drag and drop your bank slip screenshot or click to browse files",
        payment_upload_note: "Accepted formats: JPG, PNG (Max 5MB)", payment_submit: "Submit Payment Proof",
        payment_track: "Back", orders_title: "Purchase & Machining Orders",
        orders_subtitle: "Real-time telemetry and order dispatch sync with ERPNext", btn_add_to_cart: "Add to Cart",
        btn_out_of_stock: "Out of Stock", btn_remove: "Remove", btn_details: "View Details",
        toast_added_cart: "Added to Cart!", toast_removed_cart: "Component removed from cart.",
        catalog_results: "Showing {count} components",
        auth_login_title: "Client Portal", auth_login_sub: "Secure access to your telemetry dashboard.",
        auth_email: "E-mail Address", auth_password: "Password", auth_login_btn: "Authenticate",
        auth_no_account: "No manufacturing account?", auth_signup_link: "Create one",
        auth_signup_title: "New Account", auth_signup_sub: "Register for industrial hardware procurement.",
        auth_name: "Full Name / Company", auth_phone: "Mobile Number", auth_confirm_password: "Confirm Password",
        auth_signup_btn: "Create Account", auth_has_account: "Already integrated?", auth_login_link: "Sign In"
    },
    ar: {
        nav_home: "الرئيسية", nav_catalog: "جميع المنتجات", nav_orders: "تتبع الطلبات", nav_admin: "لوحة التحكم",
        home_shop_material: "تسوق حسب خامة التشغيل", home_shop_material_sub: "تصفح المكونات حسب مادة التصنيع",
        material_wood: "الأخشاب و ال MDF", material_acrylic: "الأكريليك والبلاستيك", material_metal: "الألومنيوم والمعادن",
        material_all: "عرض كل التصنيفات", home_shop_category: "تسوق حسب الفئة",
        home_shop_category_sub: "تصفح أجزاء عالية الدقة معتمدة حسب الفئة", home_trending: "المعدات الشائعة",
        home_trending_sub: "المكونات الأكثر طلباً بناءً على تكوينات ورش الآلات النشطة", home_shop_brand: "تسوق حسب العلامة التجارية المعتمدة",
        home_shop_brand_sub: "مكونات ميكانيكية أصلية من الشركات المصنعة الصناعية المعتمدة", filter_search: "بحث",
        filter_search_placeholder: "ابحث بالنموذج أو المواصفات...", filter_category: "الفئة", filter_stock: "حالة المخزون",
        filter_instock_only: "متوفر فقط", filter_max_price: "الحد الأقصى للسعر ($)", filter_brand: "العلامة التجارية",
        btn_reset_filters: "إعادة ضبط المرشحات", catalog_sort: "ترتيب: ", sort_default: "الترتيب الافتراضي",
        sort_price_asc: "السعر: من الأقل للأعلى", sort_price_desc: "السعر: من الأعلى للأقل", sort_alpha: "أ-ي حسب الاسم",
        cart_selected: "أجهزتك المختارة", cart_cost_structure: "هيكل تكلفة الطلب", cart_subtotal: "المجموع الفرعي",
        cart_shipping: "الشحن (شحن CNC افتراضي)", cart_total: "الإجمالي النهائي", cart_delivery: "عنوان التوصيل والشحن",
        cart_name: "الاسم الكامل / اسم الشركة *", cart_name_placeholder: "مثال: جون دو، شركة الآلات المحدودة",
        cart_phone: "رقم هاتف الاتصال *", cart_phone_placeholder: "مثال: +1 555-0199", cart_address: "عنوان الشحن *",
        cart_address_placeholder: "عنوان الشارع، الوحدة، المدينة، الولاية، الرمز البريدي...", cart_notes: "تفاصيل الآلات / تعليمات التوصيل",
        cart_notes_placeholder: "ملاحظات (مثل ساعات الرصيف، متطلبات الرافعة الشوكية)", cart_proceed: "متابعة لإتمام الشراء",
        payment_title: "الدفع", payment_subtitle: "لإكمال معالجة الطلب وبدء التغليف، يرجى تحويل المبلغ الإجمالي وتحميل لقطة شاشة للإيصال أدناه.",
        payment_amount_label: "المبلغ المستحق", payment_method: "اختر طريقة الدفع", payment_upload_title: "تقديم تأكيد الدفع",
        payment_upload_text: "قم بسحب وإفلات لقطة شاشة لإيصال البنك أو انقر لاستعراض الملفات", payment_upload_note: "الصيغ المقبولة: JPG، PNG (الحد الأقصى 5 ميجابايت)",
        payment_submit: "إرسال إثبات الدفع", payment_track: "رجوع", orders_title: "طلبات الشراء والآلات",
        orders_subtitle: "قياس عن بعد بالوقت الفعلي ومزامنة الإرسال مع نظام ERPNext", btn_add_to_cart: "أضف إلى السلة",
        btn_out_of_stock: "نفذت الكمية", btn_remove: "إزالة", btn_details: "عرض التفاصيل",
        toast_added_cart: "تمت الإضافة إلى السلة!", toast_removed_cart: "تم إزالة المكون من السلة.",
        catalog_results: "عرض {count} مكونات",
        auth_login_title: "بوابة العملاء", auth_login_sub: "وصول آمن إلى لوحة القياس الخاصة بك.",
        auth_email: "البريد الإلكتروني", auth_password: "كلمة المرور", auth_login_btn: "تسجيل الدخول",
        auth_no_account: "ليس لديك حساب تصنيع؟", auth_signup_link: "إنشاء حساب",
        auth_signup_title: "حساب جديد", auth_signup_sub: "سجل لشراء الأجهزة الصناعية.",
        auth_name: "الاسم الكامل / الشركة", auth_phone: "رقم الموبايل", auth_confirm_password: "تأكيد كلمة المرور",
        auth_signup_btn: "إنشاء حساب", auth_has_account: "هل لديك حساب بالفعل؟", auth_login_link: "تسجيل الدخول"
    }
};

function t(key, params = {}) {
    let str = TRANSLATIONS[state.lang] && TRANSLATIONS[state.lang][key] ? TRANSLATIONS[state.lang][key] : key;
    for (const [k, v] of Object.entries(params)) {
        str = str.replace(`{${k}}`, v);
    }
    return str;
}

function applyLanguage(lang) {
    state.lang = lang; localStorage.setItem("cnc_lang_v2", lang); document.documentElement.lang = lang;
    if (lang === 'ar') { document.body.classList.add('rtl'); } else { document.body.classList.remove('rtl'); }
    document.querySelectorAll('[data-i18n]').forEach(el => { const key = el.getAttribute('data-i18n'); el.innerText = t(key); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { const key = el.getAttribute('data-i18n-placeholder'); el.setAttribute('placeholder', t(key)); });
    const langBtnText = document.getElementById("lang-btn-text"); if(langBtnText) { langBtnText.innerText = lang === 'en' ? 'AR' : 'EN'; }
    if (typeof renderCartBadge === 'function') renderCartBadge();
    if (typeof renderCatalogGrid === 'function' && document.getElementById("catalog-view").classList.contains("active")) { renderCatalogGrid(); }
    if (typeof renderCartList === 'function' && document.getElementById("cart-view").classList.contains("active")) { renderCartList(); updateCartTotals(); }
}

function initializeState() {
    if (localStorage.getItem("cnc_products_v2")) {
        const loadedProducts = JSON.parse(localStorage.getItem("cnc_products_v2"));
        if (loadedProducts.length > 0 && !loadedProducts[0].hasOwnProperty("brand")) {
            state.products = [...INITIAL_PRODUCTS]; saveProductsToStorage();
        } else { state.products = loadedProducts; }
    } else { state.products = [...INITIAL_PRODUCTS]; saveProductsToStorage(); }
    if (localStorage.getItem("cnc_cart")) { state.cart = JSON.parse(localStorage.getItem("cnc_cart")); }
    if (localStorage.getItem("cnc_orders")) { state.orders = JSON.parse(localStorage.getItem("cnc_orders")); } else {
        state.orders = [{ id: "CNC-710892", date: new Date(Date.now() - 86400000 * 2).toISOString(), customer: { name: "Apex Machining Inc.", phone: "+1 555-0103", address: "Block 4B, Aerospace Industrial Park, Seattle WA", notes: "Forklift on-site. Deliver to loading dock A." }, items: [ { productId: "CNC-SP-01", qty: 2, price: 350.00 }, { productId: "CNC-GR-02", qty: 4, price: 120.00 } ], subtotal: 1180.00, shipping: 45.00, grandTotal: 1225.00, status: "delivered", referenceCode: "WIRE-APX-7102", receiptImg: "assets/images/linear_guide_rail.jpg" }]; saveOrdersToStorage();
    }
    if (localStorage.getItem("cnc_theme")) { state.theme = localStorage.getItem("cnc_theme"); if (state.theme === "dark") { document.body.classList.add("dark-theme"); } }
    if (localStorage.getItem("cnc_lang_v2")) { state.lang = localStorage.getItem("cnc_lang_v2"); } else { state.lang = "ar"; }
    applyLanguage(state.lang);
    if (localStorage.getItem("cnc_catalog_view_mode")) { state.catalogViewMode = localStorage.getItem("cnc_catalog_view_mode"); } else { state.catalogViewMode = "grid"; }
    if (localStorage.getItem("cnc_slides")) { state.slides = JSON.parse(localStorage.getItem("cnc_slides")); } else { state.slides = [...INITIAL_SLIDES]; saveSlidesToStorage(); }
}

function saveProductsToStorage() { localStorage.setItem("cnc_products_v2", JSON.stringify(state.products)); }
function saveCartToStorage() { localStorage.setItem("cnc_cart", JSON.stringify(state.cart)); }
function saveOrdersToStorage() { localStorage.setItem("cnc_orders", JSON.stringify(state.orders)); }
function saveSlidesToStorage() { localStorage.setItem("cnc_slides", JSON.stringify(state.slides)); }

function handleNavigation() {
    const hash = window.location.hash || "#home"; const view = hash.split("?")[0].replace("#", ""); const params = new URLSearchParams(hash.split("?")[1] || "");
    const viewSectionId = `${view}-view`; document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
    const activeSection = document.getElementById(viewSectionId);
    if (activeSection) {
        activeSection.classList.add("active"); state.activeView = view;
        document.querySelectorAll(".nav-link").forEach(link => { if (link.getAttribute("data-view") === view) { link.classList.add("active"); } else { link.classList.remove("active"); } });
        if (view === "home") { renderHomeView(); startSlideshowRotation(); } else {
            stopSlideshowRotation();
            if (view === "catalog") { const categoryFilter = params.get("category"); const brandFilter = params.get("brand"); renderCatalogView(categoryFilter, brandFilter); }
            else if (view === "detail") { const productId = params.get("id"); renderDetailView(productId); }
            else if (view === "cart") { renderCartView(); }
            else if (view === "payment") { renderPaymentView(); }
            else if (view === "orders") { renderOrdersView(); }
            else if (view === "admin") { renderAdminView(); }
        }
        window.scrollTo({ top: 0, behavior: "smooth" });
    }
}

function initToolpathCanvas() {
    const canvas = document.getElementById("toolpath-canvas"); if (!canvas) return;
    const ctx = canvas.getContext("2d"); let width = canvas.width = canvas.offsetWidth; let height = canvas.height = canvas.offsetHeight;
    window.addEventListener("resize", () => { if (!canvas) return; width = canvas.width = canvas.offsetWidth; height = canvas.height = canvas.offsetHeight; drawGrid(); });
    let mouse = { x: width / 2, y: height / 2, active: false }; let cutter = { x: width / 2, y: height / 2, speed: 0.08 }; let pathHistory = [];
    canvas.addEventListener("mousemove", (e) => { const rect = canvas.getBoundingClientRect(); mouse.x = e.clientX - rect.left; mouse.y = e.clientY - rect.top; mouse.active = true; updateFloatingGCode(mouse.x, mouse.y); });
    canvas.addEventListener("mouseleave", () => { mouse.active = false; });
    function drawGrid() {
        ctx.strokeStyle = state.theme === "dark" ? "rgba(255, 255, 255, 0.03)" : "rgba(15, 23, 42, 0.03)"; ctx.lineWidth = 1; const gridSize = 40;
        for (let x = 0; x < width; x += gridSize) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke(); }
        for (let y = 0; y < height; y += gridSize) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
    }
    function animate() {
        ctx.clearRect(0, 0, width, height); drawGrid();
        const targetX = mouse.active ? mouse.x : width / 2 + Math.sin(Date.now() / 1500) * (width / 4);
        const targetY = mouse.active ? mouse.y : height / 2 + Math.cos(Date.now() / 1000) * (height / 5);
        cutter.x += (targetX - cutter.x) * cutter.speed; cutter.y += (targetY - cutter.y) * cutter.speed;
        pathHistory.push({ x: cutter.x, y: cutter.y }); if (pathHistory.length > 100) { pathHistory.shift(); }
        if (pathHistory.length > 1) {
            ctx.beginPath(); ctx.moveTo(pathHistory[0].x, pathHistory[0].y);
            for (let i = 1; i < pathHistory.length; i++) { ctx.lineTo(pathHistory[i].x, pathHistory[i].y); }
            ctx.strokeStyle = `rgba(37, 99, 235, ${state.theme === 'dark' ? '0.45' : '0.25'})`; ctx.lineWidth = 2; ctx.stroke();
        }
        requestAnimationFrame(animate);
    }
    animate();
}

function updateFloatingGCode(x, y) {
    const activeSlide = document.querySelector(".hero-slide.active"); if (!activeSlide) return;
    const banner = activeSlide.querySelector(".gcode-scroll"); if (!banner) return;
    const mmX = (x / 2).toFixed(2); const mmY = (y / 2).toFixed(2); const feed = (1000 + Math.random() * 500).toFixed(0);
    banner.innerHTML = `<span>G90 G21 G17 G94</span><span style="color: white;">G01 X${mmX} Y${mmY} F${feed}</span><span>M03 S18000</span><span>X${(x/3).toFixed(2)} Y${(y/3).toFixed(2)}</span>`;
}

function renderHomeView() {
    renderHeroSlides();
    const categoryContainer = document.getElementById("home-category-carousels"); if (!categoryContainer) return;
    categoryContainer.innerHTML = "";
    Object.keys(CATEGORIES).forEach(key => {
        if (key === "all") return;
        const categoryProducts = state.products.filter(p => p.category === key);
        if (categoryProducts.length === 0) return;
        
        const section = document.createElement("div");
        section.className = "category-carousel-section";
        
        const header = document.createElement("div");
        header.className = "category-carousel-header";
        header.innerHTML = `
            <div style="display:flex; flex-direction:column; gap: 4px;">
                <div style="display:flex; align-items:center; gap: 12px;">
                    <h3 class="carousel-title">${CATEGORIES[key]}</h3>
                    <a href="#catalog?category=${key}" class="carousel-view-all">View All</a>
                </div>
                <p class="category-description" style="font-family: var(--font-body); font-size: 0.9rem; color: #64748B; margin: 0; max-width: 600px; line-height: 1.4; border-left: 2px solid var(--primary-blue); padding-left: 10px;">${CATEGORY_DESCRIPTIONS[key] || ""}</p>
            </div>
            <div class="carousel-nav">
                <button class="nav-btn-arrow" onclick="scrollCategoryCarousel('${key}', -1)"><i data-lucide="chevron-left"></i></button>
                <button class="nav-btn-arrow" onclick="scrollCategoryCarousel('${key}', 1)"><i data-lucide="chevron-right"></i></button>
            </div>
        `;
        
        const trackContainer = document.createElement("div");
        trackContainer.className = "category-carousel-track-wrapper";
        
        const track = document.createElement("div");
        track.className = "category-carousel-track";
        track.id = `carousel-track-${key}`;
        
        categoryProducts.forEach(prod => {
            const card = document.createElement("div");
            card.className = "product-card carousel-product-card";
            const isOutOfStock = prod.stock <= 0;
            const badgeHTML = isOutOfStock 
                ? `<span class="product-badge out-of-stock">DEPLETED</span>` 
                : `<span class="product-badge" style="background:var(--primary-blue); border-color:var(--primary-blue);">STOCK</span>`;

            card.innerHTML = `
                <div class="product-img-wrapper" onclick="window.location.hash='#detail?id=${prod.id}'">
                    <img src="${prod.image}" alt="${prod.name}" class="product-img">
                    ${badgeHTML}
                </div>
                <div class="product-info">
                    <span class="product-cat">${prod.categoryName}</span>
                    <h3 class="product-name" onclick="window.location.hash='#detail?id=${prod.id}'">${prod.name}</h3>
                    <div class="product-meta-specs">
                        <div class="spec-line">
                            <span>Brand:</span>
                            <span style="font-weight:700;">${prod.brand}</span>
                        </div>
                    </div>
                    <div class="product-bottom">
                        <span class="product-price">$${prod.price.toFixed(2)}</span>
                        <button class="card-add-btn ${isOutOfStock ? 'disabled' : ''}" onclick="addToCart('${prod.id}')" ${isOutOfStock ? 'disabled' : ''} title="${t('btn_add_to_cart')}">
                            <i data-lucide="shopping-cart"></i>
                        </button>
                    </div>
                </div>
            `;
            track.appendChild(card);
        });
        
        trackContainer.appendChild(track);
        section.appendChild(header);
        section.appendChild(trackContainer);
        categoryContainer.appendChild(section);
    });



    // Render Trending Products Shelf
    const trendingGrid = document.getElementById("home-trending-grid");
    if (trendingGrid) {
        trendingGrid.innerHTML = "";
        // Sort by sold count descending and display top 3
        const trendingProducts = [...state.products].sort((a, b) => b.sold - a.sold).slice(0, 3);
        
        trendingProducts.forEach(prod => {
            const card = document.createElement("div");
            card.className = "product-card";
            const isOutOfStock = prod.stock <= 0;
            const badgeHTML = isOutOfStock 
                ? `<span class="product-badge out-of-stock">DEPLETED</span>` 
                : `<span class="product-badge" style="background:var(--primary-blue); border-color:var(--primary-blue);">TRENDING</span>`;

            card.innerHTML = `
                <div class="product-img-wrapper" onclick="window.location.hash='#detail?id=${prod.id}'">
                    <img src="${prod.image}" alt="${prod.name}" class="product-img">
                    ${badgeHTML}
                </div>
                <div class="product-info">
                    <span class="product-cat">${prod.categoryName}</span>
                    <h3 class="product-name" onclick="window.location.hash='#detail?id=${prod.id}'">${prod.name}</h3>
                    <div class="product-meta-specs">
                        <div class="spec-line">
                            <span>Manufacturer:</span>
                            <span style="font-weight:700;">${prod.brand}</span>
                        </div>
                        <div class="spec-line">
                            <span>Sales Telemetry:</span>
                            <span style="color:var(--primary-blue); font-weight:700;">${prod.sold} units synced</span>
                        </div>
                    </div>
                    <div class="product-bottom">
                        <span class="product-price">$${prod.price.toFixed(2)}</span>
                        <button class="card-add-btn ${isOutOfStock ? 'disabled' : ''}" onclick="addToCart('${prod.id}')" ${isOutOfStock ? 'disabled' : ''} title="${t('btn_add_to_cart')}">
                            <i data-lucide="shopping-cart"></i>
                        </button>
                    </div>
                </div>
            `;
            trendingGrid.appendChild(card);
        });
    }

    // Render Brands Grid Portal
    const brandGrid = document.getElementById("home-brand-grid");
    if (brandGrid) {
        brandGrid.innerHTML = "";
        
        // Dynamic extraction of unique brands from products database
        const uniqueBrands = [...new Set(state.products.map(p => p.brand))];
        
        uniqueBrands.forEach(brand => {
            const card = document.createElement("div");
            card.className = "brand-card";
            
            let subtitle = "Certified Partner";
            if (brand === "CNCLeaders") {
                subtitle = "OEM House Parts";
            } else if (brand === "NSK Precision") {
                subtitle = "Bearings & Linears";
            } else if (brand === "Sandvik Coromant") {
                subtitle = "Premium Tooling CNC";
            } else if (brand === "Delta Electronics") {
                subtitle = "Opto-isolated Breaks";
            }

            card.innerHTML = `
                <div class="brand-logo-text"><span style="color:var(--primary-blue); font-family:var(--font-heading); font-weight:800;">[</span> ${brand} <span style="color:var(--primary-blue); font-family:var(--font-heading); font-weight:800;">]</span></div>
                <div class="brand-logo-sub">${subtitle}</div>
            `;
            
            card.onclick = () => {
                window.location.hash = `#catalog?brand=${encodeURIComponent(brand)}`;
            };
            
            brandGrid.appendChild(card);
        });
    }

    lucide.createIcons();
}

// 5.2 Catalog View Rendering
function renderCatalogView(activeCategory = null, activeBrand = null) {
    const categoryFilterList = document.getElementById("category-filter-list");
    const brandFilterList = document.getElementById("brand-filter-list");
    const productGrid = document.getElementById("catalog-product-grid");
    if (!categoryFilterList || !brandFilterList || !productGrid) return;

    // Render Filters: Category Checkboxes
    categoryFilterList.innerHTML = "";
    Object.keys(CATEGORIES).forEach(key => {
        const option = document.createElement("label");
        option.className = "checkbox-label";
        const isChecked = activeCategory 
            ? (activeCategory === key) 
            : (key === "all");

        option.innerHTML = `
            <input type="radio" name="category-filter" value="${key}" ${isChecked ? 'checked' : ''} onchange="filterAndRenderCatalog()">
            <span>${CATEGORIES[key]}</span>
        `;
        categoryFilterList.appendChild(option);
    });

    // Render Filters: Brand Checkboxes
    brandFilterList.innerHTML = "";
    const uniqueBrands = ["all", ...new Set(state.products.map(p => p.brand))];
    
    uniqueBrands.forEach(brand => {
        const option = document.createElement("label");
        option.className = "checkbox-label";
        const isChecked = activeBrand 
            ? (activeBrand === brand) 
            : (brand === "all");

        option.innerHTML = `
            <input type="radio" name="brand-filter" value="${brand}" ${isChecked ? 'checked' : ''} onchange="filterAndRenderCatalog()">
            <span>${brand === "all" ? "All Brands" : brand}</span>
        `;
        brandFilterList.appendChild(option);
    });

    filterAndRenderCatalog();
}

function filterAndRenderCatalog() {
    const searchVal = document.getElementById("catalog-search").value.toLowerCase();
    const checkedRadio = document.querySelector('input[name="category-filter"]:checked');
    const selectedCategory = checkedRadio ? checkedRadio.value : "all";
    const checkedBrandRadio = document.querySelector('input[name="brand-filter"]:checked');
    const selectedBrand = checkedBrandRadio ? checkedBrandRadio.value : "all";
    const inStockOnly = document.getElementById("filter-instock").checked;
    const maxPrice = parseFloat(document.getElementById("filter-price-range").value);
    const sortVal = document.getElementById("sort-select").value;

    // Apply Price range indicator visual label
    document.getElementById("price-slider-value").innerText = `$${maxPrice}`;

    // Filter Logic
    let filtered = state.products.filter(prod => {
        const matchesSearch = prod.name.toLowerCase().includes(searchVal) || 
                              prod.description.toLowerCase().includes(searchVal) ||
                              prod.id.toLowerCase().includes(searchVal);
                              
        const matchesCategory = (selectedCategory === "all" || prod.category === selectedCategory);
        const matchesBrand = (selectedBrand === "all" || prod.brand === selectedBrand);
        const matchesStock = !inStockOnly || prod.stock > 0;
        const matchesPrice = prod.price <= maxPrice;

        return matchesSearch && matchesCategory && matchesBrand && matchesStock && matchesPrice;
    });

    // Sorting Logic
    if (sortVal === "price-asc") {
        filtered.sort((a, b) => a.price - b.price);
    } else if (sortVal === "price-desc") {
        filtered.sort((a, b) => b.price - a.price);
    } else if (sortVal === "alpha") {
        filtered.sort((a, b) => a.name.localeCompare(b.name));
    }

    // Render Results Count text
    document.getElementById("results-count-text").innerText = t('catalog_results', {count: filtered.length});

    // Render Grid/List Cards
    const productGrid = document.getElementById("catalog-product-grid");
    productGrid.innerHTML = "";

    if (state.catalogViewMode === "list") {
        productGrid.classList.add("list-mode");
    } else {
        productGrid.classList.remove("list-mode");
    }

    if (filtered.length === 0) {
        productGrid.innerHTML = `
            <div class="drawer-empty-text" style="grid-column: 1 / -1; padding: 48px 0;">
                <p>No industrial components match your filter telemetry.</p>
            </div>
        `;
        return;
    }

    filtered.forEach(prod => {
        const card = document.createElement("div");
        const isOutOfStock = prod.stock <= 0;
        const badgeHTML = isOutOfStock 
            ? `<span class="product-badge out-of-stock">DEPLETED</span>` 
            : ``;

        if (state.catalogViewMode === "list") {
            card.className = "product-card list-layout";
            card.innerHTML = `
                <div class="product-img-wrapper" onclick="window.location.hash='#detail?id=${prod.id}'">
                    <img src="${prod.image}" alt="${prod.name}" class="product-img">
                    ${badgeHTML}
                </div>
                <div class="product-info-list">
                    <div class="product-main-details">
                        <span class="product-cat">${prod.categoryName}</span>
                        <h3 class="product-name" onclick="window.location.hash='#detail?id=${prod.id}'">${prod.name}</h3>
                        <p class="product-desc-short">${prod.description.substring(0, 130)}...</p>
                    </div>
                    <div class="product-specs-list">
                        <div class="product-meta-specs">
                            <div class="spec-line">
                                <span>ERP ID:</span>
                                <span>${prod.id}</span>
                            </div>
                            <div class="spec-line">
                                <span>Availability:</span>
                                <span>${prod.stock} units</span>
                            </div>
                            <div class="spec-line">
                                <span>Brand:</span>
                                <span>${prod.brand}</span>
                            </div>
                        </div>
                    </div>
                    <div class="product-actions-list">
                        <span class="product-price">$${prod.price.toFixed(2)}</span>
                        <button class="btn btn-primary btn-sm ${isOutOfStock ? 'disabled' : ''}" onclick="addToCart('${prod.id}')" ${isOutOfStock ? 'disabled' : ''}>
                            <i data-lucide="shopping-cart" style="width:16px; height:16px; margin-right:6px; display:inline-block; vertical-align:middle;"></i>${t('btn_add_to_cart')}
                        </button>
                    </div>
                </div>
            `;
        } else {
            card.className = "product-card";
            card.innerHTML = `
                <div class="product-img-wrapper" onclick="window.location.hash='#detail?id=${prod.id}'">
                    <img src="${prod.image}" alt="${prod.name}" class="product-img">
                    ${badgeHTML}
                </div>
                <div class="product-info">
                    <span class="product-cat">${prod.categoryName}</span>
                    <h3 class="product-name" onclick="window.location.hash='#detail?id=${prod.id}'">${prod.name}</h3>
                    <div class="product-meta-specs">
                        <div class="spec-line">
                            <span>ERP ID:</span>
                            <span>${prod.id}</span>
                        </div>
                        <div class="spec-line">
                            <span>Stock Availability:</span>
                            <span>${prod.stock} units</span>
                        </div>
                    </div>
                    <div class="product-bottom">
                        <span class="product-price">$${prod.price.toFixed(2)}</span>
                        <button class="card-add-btn ${isOutOfStock ? 'disabled' : ''}" onclick="addToCart('${prod.id}')" ${isOutOfStock ? 'disabled' : ''} title="${t('btn_add_to_cart')}">
                            <i data-lucide="shopping-cart"></i>
                        </button>
                    </div>
                </div>
            `;
        }
        productGrid.appendChild(card);
    });

    lucide.createIcons();
}

// 5.3 Product Detail Page rendering
function renderDetailView(productId) {
    const detailContainer = document.getElementById("product-detail-container");
    if (!detailContainer) return;

    const prod = state.products.find(p => p.id === productId);
    if (!prod) {
        detailContainer.innerHTML = `<p>Error: Component [${productId}] not found in ERPNext synchronized inventory database.</p>`;
        return;
    }

    const isOutOfStock = prod.stock <= 0;

    // Render specification table rows
    let specRows = "";
    Object.keys(prod.specs).forEach(specKey => {
        specRows += `
            <tr>
                <td class="spec-name">${specKey}</td>
                <td class="spec-val">${prod.specs[specKey]}</td>
            </tr>
        `;
    });

    // Render detail layout
    detailContainer.innerHTML = `
        <div class="detail-layout">
            <!-- Left Side: Image Gallery -->
            <div class="detail-gallery">
                <div class="detail-main-img-box">
                    <img src="${prod.image}" alt="${prod.name}" id="detail-main-image-element" class="detail-main-img">
                </div>
                <div class="detail-gallery-thumbs">
                    <div class="gallery-thumb active" onclick="updateMainDetailImage('${prod.image}', this)">
                        <img src="${prod.image}" alt="Angle 1">
                    </div>
                    <div class="gallery-thumb" onclick="updateMainDetailImage('${prod.image}', this)">
                        <img src="${prod.image}" alt="Angle 2" style="filter: brightness(0.9) contrast(1.1);">
                    </div>
                </div>
            </div>

            <!-- Right Side: Details Metadata & Cart add Actions -->
            <div class="detail-meta-panel">
                <span class="detail-cat">${prod.categoryName}</span>
                <h1 class="detail-title">${prod.name}</h1>
                
                <div class="detail-price-status">
                    <span class="detail-price">$${prod.price.toFixed(2)}</span>
                    <div class="stock-indicator">
                        <span class="dot-status ${isOutOfStock ? 'dot-outofstock' : 'dot-instock'}"></span>
                        <span style="color: ${isOutOfStock ? '#EF4444' : '#22C55E'}">
                            ${isOutOfStock ? t('btn_out_of_stock') : `In Stock: ${prod.stock} units`}
                        </span>
                    </div>
                </div>

                <p class="detail-desc">${prod.description}</p>

                <h3 class="specs-table-title">Product Calibration Specs</h3>
                <table class="specs-table">
                    <tbody>
                        <tr>
                            <td class="spec-name">ERP Database Ref</td>
                            <td class="spec-val" style="color: var(--primary-blue);">${prod.id}</td>
                        </tr>
                        ${specRows}
                    </tbody>
                </table>

                <div class="detail-actions">
                    <div class="qty-spinner">
                        <button class="qty-btn" onclick="adjustDetailQty(-1)">-</button>
                        <input type="text" value="1" id="detail-qty-input" class="qty-val" readonly>
                        <button class="qty-btn" onclick="adjustDetailQty(1)">+</button>
                    </div>
                    <button class="btn btn-primary ${isOutOfStock ? 'disabled' : ''}" style="flex-grow:1;" onclick="addDetailToCart('${prod.id}')" ${isOutOfStock ? 'disabled' : ''}>
                        <i data-lucide="shopping-cart"></i> ${t('btn_add_to_cart')}
                    </button>
                </div>
            </div>
        </div>

        <!-- Optional: Related Products -->
        <div class="related-section">
            <h2 class="specs-table-title" style="font-size: 1.5rem; margin-bottom: 24px;">Similar Engineering Components</h2>
            <div class="featured-grid" id="detail-related-grid"></div>
        </div>
    `;

    // Render related products dynamically
    const relatedGrid = document.getElementById("detail-related-grid");
    if (relatedGrid) {
        relatedGrid.innerHTML = "";
        const items = state.products.filter(p => p.category === prod.category && p.id !== prod.id).slice(0, 3);
        
        if (items.length === 0) {
            // Grab any other items if none in same category
            state.products.filter(p => p.id !== prod.id).slice(0, 3).forEach(item => items.push(item));
        }

        items.forEach(item => {
            const card = document.createElement("div");
            card.className = "product-card";
            card.innerHTML = `
                <div class="product-img-wrapper" onclick="window.location.hash='#detail?id=${item.id}'">
                    <img src="${item.image}" alt="${item.name}" class="product-img">
                </div>
                <div class="product-info">
                    <span class="product-cat">${item.categoryName}</span>
                    <h4 class="product-name" onclick="window.location.hash='#detail?id=${item.id}'">${item.name}</h4>
                    <div class="product-bottom" style="margin-top: 12px;">
                        <span class="product-price">$${item.price.toFixed(2)}</span>
                        <button class="card-add-btn" onclick="addToCart('${item.id}')">
                            <i data-lucide="shopping-cart"></i>
                        </button>
                    </div>
                </div>
            `;
            relatedGrid.appendChild(card);
        });
    }

    lucide.createIcons();
}

function updateMainDetailImage(src, element) {
    const mainImg = document.getElementById("detail-main-image-element");
    if (mainImg) {
        mainImg.src = src;
    }
    document.querySelectorAll(".gallery-thumb").forEach(thumb => thumb.classList.remove("active"));
    element.classList.add("active");
}

function adjustDetailQty(amount) {
    const input = document.getElementById("detail-qty-input");
    if (input) {
        let val = parseInt(input.value) + amount;
        if (val < 1) val = 1;
        input.value = val;
    }
}

// 5.4 Cart View Page Rendering
function renderCartView() {
    const cartList = document.getElementById("cart-page-list");
    if (!cartList) return;

    cartList.innerHTML = "";

    if (state.cart.length === 0) {
        cartList.innerHTML = `
            <div class="drawer-empty-text" style="padding: 48px 0; text-align: center;">
                <p>Your shopping cart is currently empty.</p>
                <a href="#catalog" class="btn btn-secondary btn-sm" style="margin-top: 16px;">Browse Parts Catalog</a>
            </div>
        `;
        updateCartTotals(0);
        return;
    }

    let subtotal = 0;

    state.cart.forEach(item => {
        const prod = state.products.find(p => p.id === item.productId);
        if (!prod) return;

        const rowTotal = prod.price * item.qty;
        subtotal += rowTotal;

        const row = document.createElement("div");
        row.className = "cart-item";
        row.innerHTML = `
            <img src="${prod.image}" alt="${prod.name}" class="cart-item-img">
            <div class="cart-item-info">
                <a href="#detail?id=${prod.id}" class="cart-item-title">${prod.name}</a>
                <div class="cart-item-cat">ERP ID: ${prod.id} | Price: $${prod.price.toFixed(2)}</div>
            </div>
            <div class="qty-spinner" style="margin-right: 16px;">
                <button class="qty-btn" onclick="updateCartItemQty('${prod.id}', -1)">-</button>
                <input type="text" value="${item.qty}" class="qty-val" readonly>
                <button class="qty-btn" onclick="updateCartItemQty('${prod.id}', 1)">+</button>
            </div>
            <div class="cart-item-price" style="min-width: 90px; text-align: right;">$${rowTotal.toFixed(2)}</div>
            <button class="cart-item-remove-btn" onclick="removeCartItem('${prod.id}')" title="${t('btn_remove')}">
                <i data-lucide="trash-2"></i>
            </button>
        `;
        cartList.appendChild(row);
    });

    updateCartTotals(subtotal);
    lucide.createIcons();
}

function updateCartTotals(subtotal) {
    // Shipping simulation: free shipping if > $500, otherwise flat $35 industrial freight
    const shipping = subtotal > 500 || subtotal === 0 ? 0.00 : 35.00;
    const grandtotal = subtotal + shipping;

    document.getElementById("cart-subtotal").innerText = `$${subtotal.toFixed(2)}`;
    document.getElementById("cart-shipping").innerText = shipping === 0 ? "FREE FREIGHT" : `$${shipping.toFixed(2)}`;
    document.getElementById("cart-grandtotal").innerText = `$${grandtotal.toFixed(2)}`;
}

// Payment Methods Configuration & Interactive Selector
const PAYMENT_METHODS = {
    instapay: {
        name: "InstaPay",
        label: "InstaPay Address / Mobile",
        value: "01555233700",
        recipient: "CNCLeaders Distribution Corp",
        note: "Instant payment transfer via InstaPay App."
    },
    vodafone: {
        name: "Vodafone Cash",
        label: "Vodafone Mobile Wallet",
        value: "12344565555",
        recipient: "CNCLeaders Mobile Pay",
        note: "Direct wallet transfer to our official Vodafone Cash number."
    },
    etisalat: {
        name: "Etisalat Cash",
        label: "Etisalat Mobile Wallet",
        value: "01234345435",
        recipient: "CNCLeaders Mobile Pay",
        note: "Direct wallet transfer to our official Etisalat Cash number."
    },
    bank: {
        name: "Bank Wire",
        label: "IBAN / Account Number",
        value: "US99 ICBC 0199 2384 1029 99",
        recipient: "Industrial Commerce Bank (ICB) - CNCLeaders Distribution Corp",
        note: "Traditional Bank Wire transfer (BIC/Routing: ICB109XX)."
    }
};

window.selectPaymentMethod = function(methodKey) {
    const cards = document.querySelectorAll(".payment-method-card");
    cards.forEach(card => {
        if (card.dataset.method === methodKey) {
            card.classList.add("active");
        } else {
            card.classList.remove("active");
        }
    });

    const detailsBox = document.getElementById("payment-details-box");
    if (!detailsBox) return;

    const method = PAYMENT_METHODS[methodKey];
    if (!method) return;

    detailsBox.innerHTML = `
        <div class="method-details-wrapper animate-fade-in">
            <div class="method-details-header">
                <span class="details-title">${method.name} Details</span>
                <span class="details-note">${method.note}</span>
            </div>
            <div class="details-row">
                <div class="details-item">
                    <span class="details-lbl">Account Recipient</span>
                    <span class="details-val">${method.recipient}</span>
                </div>
                <div class="details-item">
                    <span class="details-lbl">${method.label}</span>
                    <div class="details-val-copy-container">
                        <span class="details-val highlight-val" id="payment-dest-val">${method.value}</span>
                        <button class="copy-btn" onclick="navigator.clipboard.writeText('${method.value}'); showToast('${method.name} details copied!')" title="Copy Number">
                            <i data-lucide="copy" class="small-copy-icon"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (window.lucide) {
        window.lucide.createIcons();
    }
};

// 5.5 Payment View rendering
function renderPaymentView() {
    // Retrieve pending order details from sessionStorage
    const currentCheckout = JSON.parse(sessionStorage.getItem("cnc_current_checkout"));
    if (!currentCheckout) {
        window.location.hash = "#cart";
        return;
    }

    document.getElementById("payment-amount").innerText = `$${currentCheckout.grandTotal.toFixed(2)}`;
    document.getElementById("payment-ref-text").innerText = `Order Reference ID: #${currentCheckout.id}`;
    
    // Set submit button behavior
    const submitBtn = document.getElementById("submit-payment-btn");
    submitBtn.onclick = () => submitPaymentProof(currentCheckout);

    // Default select InstaPay on load
    window.selectPaymentMethod('instapay');

    resetUploadZone();
}

function resetUploadZone() {
    state.pendingReceiptFile = null;
    const dropZone = document.getElementById("payment-drop-zone");
    const previewArea = document.getElementById("upload-preview-area");
    const submitBtn = document.getElementById("submit-payment-btn");
    
    if (previewArea) previewArea.style.display = "none";
    if (dropZone) dropZone.classList.remove("hover");
    if (submitBtn) {
        submitBtn.classList.add("disabled");
        submitBtn.disabled = true;
    }
}

// 5.6 Orders View tracking history
function renderOrdersView() {
    const ordersList = document.getElementById("orders-history-list");
    if (!ordersList) return;

    ordersList.innerHTML = "";

    if (state.orders.length === 0) {
        ordersList.innerHTML = `
            <div class="drawer-empty-text" style="padding: 64px 0; text-align: center;">
                <p>No active purchases found in local tracking cache. Sync with ERPNext is healthy.</p>
            </div>
        `;
        return;
    }

    // Render most recent orders first
    [...state.orders].reverse().forEach(order => {
        const orderCard = document.createElement("div");
        orderCard.className = "order-history-card";
        
        let statusText = "Pending Wire Verification";
        if (order.status === "paid") statusText = "Payment Verified & Processing";
        if (order.status === "shipped") statusText = "Shipped from Depot";
        if (order.status === "delivered") statusText = "Delivered";

        // Determine step indices
        let step1Class = "completed"; // Wire submission is always done
        let step2Class = (order.status === "paid" || order.status === "shipped" || order.status === "delivered") ? "completed" : "active";
        let step3Class = (order.status === "shipped" || order.status === "delivered") ? "completed" : (order.status === "paid" ? "active" : "");
        let step4Class = (order.status === "delivered") ? "completed" : (order.status === "shipped" ? "active" : "");

        let progressWidth = "0%";
        if (order.status === "paid") progressWidth = "33%";
        if (order.status === "shipped") progressWidth = "66%";
        if (order.status === "delivered") progressWidth = "100%";

        // Render product item rows
        let itemsHtml = "";
        order.items.forEach(item => {
            const p = state.products.find(prod => prod.id === item.productId);
            const name = p ? p.name : `Component ${item.productId}`;
            itemsHtml += `
                <div class="details-prod-item">
                    <span class="details-prod-name">${name}</span>
                    <span class="details-prod-qty">x${item.qty}</span>
                    <span class="details-prod-price">$${(item.price * item.qty).toFixed(2)}</span>
                </div>
            `;
        });

        // Add receipt preview if present
        let receiptPreviewHTML = "";
        if (order.receiptImg) {
            receiptPreviewHTML = `
                <div class="receipt-preview-box">
                    <span class="receipt-lbl">Receipt Proof Sync Details</span>
                    <img src="${order.receiptImg}" alt="Receipt image" class="receipt-img-thumb" onclick="openReceiptInNewWindow('${order.receiptImg}')" title="Zoom view">
                </div>
            `;
        }

        orderCard.innerHTML = `
            <div class="order-card-header">
                <div class="order-header-main">
                    <span class="order-id-badge">Order ID: #${order.id}</span>
                    <span class="order-date-text">Placed on ${new Date(order.date).toLocaleString()}</span>
                </div>
                <div class="order-status-flex">
                    <span class="order-status-pill status-${order.status}">${statusText}</span>
                </div>
            </div>
            
            <div class="order-card-body">
                <div class="order-meta-info-grid">
                    <div class="meta-field">
                        <span class="meta-lbl">Shipment Address</span>
                        <span class="meta-val">${order.customer.name}</span>
                        <span class="meta-val" style="font-size:0.85rem; color:var(--text-muted); font-weight:normal;">${order.customer.address}</span>
                    </div>
                    <div class="meta-field">
                        <span class="meta-lbl">Contact Phone</span>
                        <span class="meta-val">${order.customer.phone}</span>
                    </div>
                    <div class="meta-field text-right">
                        <span class="meta-lbl">Wire Total Verified</span>
                        <span class="meta-val" style="color:var(--primary-blue); font-size:1.15rem;">$${order.grandTotal.toFixed(2)}</span>
                    </div>
                </div>

                <!-- Horizontal Stepper Progress Flow -->
                <div class="tracking-flow">
                    <div class="tracking-progress-bar" style="width: ${progressWidth};"></div>
                    <div class="track-step completed">
                        <div class="step-node"><i data-lucide="check" style="width:14px; height:14px;"></i></div>
                        <span class="step-label">Wire Sent</span>
                    </div>
                    <div class="track-step ${step2Class}">
                        <div class="step-node">2</div>
                        <span class="step-label">ERP Sync</span>
                    </div>
                    <div class="track-step ${step3Class}">
                        <div class="step-node">3</div>
                        <span class="step-label">Shipped</span>
                    </div>
                    <div class="track-step ${step4Class}">
                        <div class="step-node">4</div>
                        <span class="step-label">Arrived</span>
                    </div>
                </div>

                <!-- Expandable details -->
                <button class="order-details-toggle" onclick="toggleOrderDetails(this)">
                    <span>Show Machinery Specs</span>
                    <i data-lucide="chevron-down" style="width:16px; height:16px;"></i>
                </button>

                <div class="order-details-drawer">
                    <div class="details-product-list">
                        ${itemsHtml}
                    </div>
                    <div class="details-prod-item" style="border-top:1px dashed var(--border-subtle); padding-top:8px; font-weight:bold;">
                        <span>Freight Subtotal</span>
                        <span>$${order.subtotal.toFixed(2)}</span>
                    </div>
                    <div class="details-prod-item" style="font-weight:bold;">
                        <span>Shipping Cargo Fee</span>
                        <span>$${order.shipping.toFixed(2)}</span>
                    </div>
                    ${receiptPreviewHTML}
                </div>
            </div>
        `;
        ordersList.appendChild(orderCard);
    });

    lucide.createIcons();
}

function toggleOrderDetails(button) {
    const drawer = button.nextElementSibling;
    const icon = button.querySelector("[data-lucide]");
    
    drawer.classList.toggle("open");
    
    if (drawer.classList.contains("open")) {
        button.querySelector("span").innerText = "Hide Machinery Specs";
        if (icon) icon.style.transform = "rotate(180deg)";
    } else {
        button.querySelector("span").innerText = "Show Machinery Specs";
        if (icon) icon.style.transform = "rotate(0deg)";
    }
}

function openReceiptInNewWindow(src) {
    const w = window.open();
    w.document.write(`<img src="${src}" style="max-width:100%; max-height:100vh; display:block; margin:auto;" />`);
}

// 5.7 Admin Dashboard rendering
function renderAdminView() {
    // Set active sidebar link status
    document.querySelectorAll(".admin-menu-link").forEach(link => {
        if (link.getAttribute("data-tab") === state.activeAdminTab) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });

    // Hide/Show Admin Tab Contents
    document.querySelectorAll(".admin-tab-content").forEach(content => {
        if (content.id === `admin-tab-${state.activeAdminTab}`) {
            content.classList.add("active");
        } else {
            content.classList.remove("active");
        }
    });

    if (state.activeAdminTab === "analytics") {
        renderAdminAnalytics();
    } else if (state.activeAdminTab === "inventory") {
        renderAdminInventory();
    } else if (state.activeAdminTab === "orders") {
        renderAdminOrdersApproval();
    } else if (state.activeAdminTab === "slideshow") {
        renderAdminSlideshowTable();
    }
}

function renderAdminAnalytics() {
    // 1. Calculate metrics
    let totalRevenue = 0;
    let approvedOrdersCount = 0;
    
    state.orders.forEach(order => {
        if (order.status !== "pending") { // Wire is confirmed/approved
            totalRevenue += order.grandTotal;
            approvedOrdersCount++;
        }
    });

    document.getElementById("admin-revenue-text").innerText = `$${totalRevenue.toFixed(2)}`;
    document.getElementById("admin-orders-text").innerText = `${state.orders.length} Synced`;
    
    const conversionVal = state.orders.length > 0 ? ((approvedOrdersCount / state.orders.length) * 100).toFixed(1) : "0.0";
    document.getElementById("admin-conversion-text").innerText = `${conversionVal}%`;

    // 2. Render SVG Analytics Chart
    const chartContainer = document.getElementById("sales-chart-container");
    if (!chartContainer) return;

    // Build data representation
    let points = [35, 75, 45, 115, 95, 185, 145, 230]; // hourly dummy activity
    if (state.orders.length > 0) {
        // Boost last elements if orders are added
        points[points.length - 1] += state.orders.length * 20;
    }

    const svgWidth = chartContainer.offsetWidth || 500;
    const svgHeight = 240;
    const padding = 30;
    const maxVal = Math.max(...points) * 1.1;

    // Create polyline coordinates
    let polylineCoords = "";
    const xStep = (svgWidth - padding * 2) / (points.length - 1);
    
    points.forEach((val, index) => {
        const x = padding + index * xStep;
        const y = svgHeight - padding - (val / maxVal) * (svgHeight - padding * 2);
        polylineCoords += `${x},${y} `;
    });

    let gridLinesHTML = "";
    // Draw 3 horizontal gridlines
    for (let i = 1; i <= 3; i++) {
        const gridY = padding + (i / 4) * (svgHeight - padding * 2);
        gridLinesHTML += `
            <line x1="${padding}" y1="${gridY}" x2="${svgWidth - padding}" y2="${gridY}" stroke="var(--border-subtle)" stroke-dasharray="4,4" />
        `;
    }

    chartContainer.innerHTML = `
        <svg width="100%" height="100%" viewBox="0 0 ${svgWidth} ${svgHeight}" style="overflow:visible;">
            ${gridLinesHTML}
            <polyline
                fill="none"
                stroke="var(--primary-blue)"
                stroke-width="3"
                points="${polylineCoords}"
            />
            <!-- Dots on peaks -->
            ${points.map((val, idx) => {
                const x = padding + idx * xStep;
                const y = svgHeight - padding - (val / maxVal) * (svgHeight - padding * 2);
                return `
                    <circle cx="${x}" cy="${y}" r="5" fill="var(--bg-dark)" stroke="var(--primary-blue)" stroke-width="2" />
                `;
            }).join("")}
        </svg>
    `;
}

function renderAdminInventory() {
    const tableBody = document.getElementById("admin-inventory-rows");
    if (!tableBody) return;

    tableBody.innerHTML = "";
    state.products.forEach(prod => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><code style="font-weight:bold; color:var(--primary-blue);">${prod.id}</code></td>
            <td>
                <div style="display:flex; align-items:center; gap:12px;">
                    <img src="${prod.image}" alt="${prod.name}" class="admin-img-thumb">
                    <span style="font-weight:600;">${prod.name}</span>
                </div>
            </td>
            <td>${prod.categoryName}</td>
            <td style="font-weight:bold;">$${prod.price.toFixed(2)}</td>
            <td>
                <span class="${prod.stock <= 0 ? 'text-blue' : ''}" style="font-weight:bold;">${prod.stock} units</span>
            </td>
            <td>
                <span class="badge-sync">
                    <span class="dot-pulse"></span> ERP Syncing
                </span>
            </td>
            <td>
                <input type="number" class="stock-input" value="${prod.stock}" min="0" onchange="overrideInventoryStock('${prod.id}', this.value)">
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

function renderAdminOrdersApproval() {
    const tableBody = document.getElementById("admin-receipt-rows");
    if (!tableBody) return;

    tableBody.innerHTML = "";
    const pendingOrders = state.orders.filter(o => o.status === "pending");

    if (pendingOrders.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align:center; padding: 48px; color:var(--text-muted);">
                    All pending manual bank wires have been processed. Queue is clear!
                </td>
            </tr>
        `;
        return;
    }

    pendingOrders.forEach(order => {
        const tr = document.createElement("tr");
        
        let filePreviewHTML = `<span style="font-size:0.8rem; color:var(--text-muted);">None uploaded</span>`;
        if (order.receiptImg) {
            filePreviewHTML = `
                <img src="${order.receiptImg}" alt="receipt" class="admin-img-thumb" onclick="openReceiptInNewWindow('${order.receiptImg}')" style="cursor:pointer;" title="View Wire screenshot">
            `;
        }

        tr.innerHTML = `
            <td><code style="font-weight:bold;">#${order.id}</code></td>
            <td>${new Date(order.date).toLocaleDateString()}</td>
            <td>
                <div style="font-weight:600;">${order.customer.name}</div>
                <div style="font-size:0.8rem; color:var(--text-muted);">${order.customer.phone}</div>
            </td>
            <td style="font-weight:bold; color:var(--primary-blue);">$${order.grandTotal.toFixed(2)}</td>
            <td>${filePreviewHTML}</td>
            <td>
                <div style="display:flex; gap:8px;">
                    <button class="btn btn-primary btn-sm" onclick="approveOrderPayment('${order.id}')" style="padding:6px 10px;">
                        Approve Payment
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="rejectOrderPayment('${order.id}')" style="padding:6px 10px; color:#EF4444; border-color:#EF4444;">
                        Cancel
                    </button>
                </div>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

// --- 6. INTERACTIVE UTILITIES & TRIGGERS (ADD TO CART, DRAWER ACTIONS, QUANTITIES) ---

// Dynamic popup toasts
function showToast(message, icon = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `
        <i data-lucide="${icon === 'success' ? 'check-circle' : 'info'}" class="toast-icon"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    lucide.createIcons();

    // Trigger animation removal
    setTimeout(() => {
        toast.classList.add("fade-out");
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Cart Drawer Toggles
function initCartDrawer() {
    const cartToggle = document.getElementById("cart-toggle-btn");
    const closeDrawer = document.getElementById("close-drawer-btn");
    const drawerOverlay = document.getElementById("cart-drawer-overlay");
    const drawer = document.getElementById("cart-drawer");

    const openAction = () => {
        renderCartDrawerBody();
        drawer.classList.add("active");
        drawerOverlay.classList.add("active");
    };

    const closeAction = () => {
        drawer.classList.remove("active");
        drawerOverlay.classList.remove("active");
    };

    if (cartToggle) cartToggle.addEventListener("click", openAction);
    if (closeDrawer) closeDrawer.addEventListener("click", closeAction);
    if (drawerOverlay) drawerOverlay.addEventListener("click", closeAction);

    // Also close drawer when clicking the checkout button in drawer
    const checkoutBtn = document.getElementById("drawer-checkout-btn");
    if (checkoutBtn) checkoutBtn.addEventListener("click", closeAction);
}

function renderCartDrawerBody() {
    const body = document.getElementById("cart-drawer-body");
    const subtotalText = document.getElementById("drawer-subtotal");
    const checkoutBtn = document.getElementById("drawer-checkout-btn");
    if (!body) return;

    body.innerHTML = "";
    
    if (state.cart.length === 0) {
        body.innerHTML = `<p class="drawer-empty-text">Your hardware buffer cart is empty.</p>`;
        if (subtotalText) subtotalText.innerText = "$0.00";
        if (checkoutBtn) checkoutBtn.classList.add("disabled");
        updateCartBadgeCount();
        return;
    }

    if (checkoutBtn) checkoutBtn.classList.remove("disabled");
    let subtotal = 0;

    state.cart.forEach(item => {
        const prod = state.products.find(p => p.id === item.productId);
        if (!prod) return;

        const rowTotal = prod.price * item.qty;
        subtotal += rowTotal;

        const card = document.createElement("div");
        card.className = "cart-item";
        card.innerHTML = `
            <img src="${prod.image}" alt="${prod.name}" class="cart-item-img" style="width: 50px; height: 50px;">
            <div class="cart-item-info" style="gap:2px;">
                <h4 class="cart-item-title" style="font-size:0.85rem; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${prod.name}</h4>
                <div class="cart-item-cat" style="font-size: 0.7rem;">Qty: ${item.qty} | Price: $${prod.price.toFixed(2)}</div>
            </div>
            <div style="font-weight:700; font-size:0.9rem; margin-right:8px;">$${rowTotal.toFixed(2)}</div>
            <button class="cart-item-remove-btn" onclick="removeCartItem('${prod.id}', true)" style="padding: 4px;">
                <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
            </button>
        `;
        body.appendChild(card);
    });

    if (subtotalText) subtotalText.innerText = `$${subtotal.toFixed(2)}`;
    updateCartBadgeCount();
    lucide.createIcons();
}

function updateCartBadgeCount() {
    const badge = document.getElementById("cart-badge");
    if (!badge) return;

    const count = state.cart.reduce((sum, item) => sum + item.qty, 0);
    badge.innerText = count;
}

// Add Item from Product Card Grid
window.addToCart = function(productId) {
    const prod = state.products.find(p => p.id === productId);
    if (!prod || prod.stock <= 0) return;

    const existing = state.cart.find(item => item.productId === productId);
    if (existing) {
        if (existing.qty < prod.stock) {
            existing.qty++;
            showToast(`${prod.name} quantity increased.`, "success");
        } else {
            showToast(`Cannot exceed current ERPNext stock limit (${prod.stock}).`, "info");
            return;
        }
    } else {
        state.cart.push({ productId: productId, qty: 1 });
        showToast(t('toast_added_cart'), "success");
    }

    saveCartToStorage();
    updateCartBadgeCount();
    renderCartDrawerBody();
};

// Add Item from Detail View (with specific Qty Spinner)
window.addDetailToCart = function(productId) {
    const prod = state.products.find(p => p.id === productId);
    if (!prod || prod.stock <= 0) return;

    const qtyInput = document.getElementById("detail-qty-input");
    const qtyToAdd = qtyInput ? parseInt(qtyInput.value) : 1;

    const existing = state.cart.find(item => item.productId === productId);
    const currentQty = existing ? existing.qty : 0;

    if (currentQty + qtyToAdd > prod.stock) {
        showToast(`Cannot exceed ERP stock limits. Active cap is ${prod.stock} units.`, "info");
        return;
    }

    if (existing) {
        existing.qty += qtyToAdd;
    } else {
        state.cart.push({ productId: productId, qty: qtyToAdd });
    }

    showToast(`Successfully added ${qtyToAdd} unit(s) of ${prod.name}.`, "success");
    saveCartToStorage();
    updateCartBadgeCount();
    window.location.hash = "#cart";
};

// Edit Qty Spinner in Cart Page
window.updateCartItemQty = function(productId, delta) {
    const item = state.cart.find(i => i.productId === productId);
    const prod = state.products.find(p => p.id === productId);
    if (!item || !prod) return;

    let newVal = item.qty + delta;
    
    if (newVal > prod.stock) {
        showToast(`Cannot exceed ERP stock limits. Limit: ${prod.stock} units.`, "info");
        return;
    }

    if (newVal <= 0) {
        removeCartItem(productId);
        return;
    }

    item.qty = newVal;
    saveCartToStorage();
    updateCartBadgeCount();
    renderCartView();
};

// Remove Item from Cart
window.removeCartItem = function(productId, isDrawer = false) {
    state.cart = state.cart.filter(item => item.productId !== productId);
    saveCartToStorage();
    updateCartBadgeCount();
    
    if (isDrawer) {
        renderCartDrawerBody();
    } else {
        renderCartView();
    }
    showToast(t('toast_removed_cart'), "info");
};

// --- 7. CHECKOUT FORM & PAYMENT VERIFICATION UPLOAD PROCESS ---
function initCheckoutForm() {
    const form = document.getElementById("checkout-delivery-form");
    if (!form) return;

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        
        if (state.cart.length === 0) return;

        // Extract pricing subtotals
        let subtotal = 0;
        state.cart.forEach(item => {
            const p = state.products.find(prod => prod.id === item.productId);
            if (p) subtotal += p.price * item.qty;
        });

        const shipping = subtotal > 500 ? 0.00 : 35.00;
        const grandTotal = subtotal + shipping;

        // Form fields payload
        const checkoutPayload = {
            id: "CNC-" + Math.floor(100000 + Math.random() * 900000), // Random Order reference
            date: new Date().toISOString(),
            customer: {
                name: document.getElementById("cust-name").value,
                phone: document.getElementById("cust-phone").value,
                address: document.getElementById("cust-address").value,
                notes: document.getElementById("cust-notes").value
            },
            items: [...state.cart],
            subtotal: subtotal,
            shipping: shipping,
            grandTotal: grandTotal,
            status: "pending",
            referenceCode: "",
            receiptImg: ""
        };

        // Cache checkout in Session to hold reference during wire validation
        sessionStorage.setItem("cnc_current_checkout", JSON.stringify(checkoutPayload));
        
        // Reset inputs and navigate
        form.reset();
        window.location.hash = "#payment";
    });
}

function initPaymentSlipUpload() {
    const dropZone = document.getElementById("payment-drop-zone");
    const fileInput = document.getElementById("payment-file-input");
    const submitBtn = document.getElementById("submit-payment-btn");
    const removeBtn = document.getElementById("remove-receipt-btn");

    if (!dropZone || !fileInput) return;

    // Trigger browse file click on zone tap
    dropZone.addEventListener("click", () => {
        if (!state.pendingReceiptFile) {
            fileInput.click();
        }
    });

    // Drag-and-Drop Visual States
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("hover");
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("hover");
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("hover");
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleUploadedFile(files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            handleUploadedFile(files[0]);
        }
    });

    // Clear Upload zone click listener
    if (removeBtn) {
        removeBtn.addEventListener("click", (e) => {
            e.stopPropagation(); // Avoid triggering dropzone input browse
            resetUploadZone();
        });
    }
}

function handleUploadedFile(file) {
    if (!file.type.match("image.*")) {
        showToast("Error: Upload must be a valid image file (screenshot/photo).", "info");
        return;
    }

    state.pendingReceiptFile = file;
    
    // Read and render file preview path
    const reader = new FileReader();
    reader.onload = (e) => {
        const previewImg = document.getElementById("receipt-preview-img");
        const previewArea = document.getElementById("upload-preview-area");
        const fileNameLabel = document.getElementById("receipt-file-name");
        const submitBtn = document.getElementById("submit-payment-btn");

        if (previewImg) previewImg.src = e.target.result;
        if (previewArea) previewArea.style.display = "flex";
        if (fileNameLabel) fileNameLabel.innerText = file.name;
        
        // Enable Submission Button
        if (submitBtn) {
            submitBtn.classList.remove("disabled");
            submitBtn.disabled = false;
        }
    };
    reader.readAsDataURL(file);
}

function submitPaymentProof(orderData) {
    if (!state.pendingReceiptFile) return;

    // Attach base64 image data to order payload
    const previewImg = document.getElementById("receipt-preview-img");
    orderData.receiptImg = previewImg ? previewImg.src : "";
    orderData.referenceCode = "REF-" + Math.floor(1000 + Math.random() * 9000);

    // Save order database
    state.orders.push(orderData);
    saveOrdersToStorage();

    // Reduce product inventory levels locally and increment sold count (ERPNext validation simulation)
    orderData.items.forEach(item => {
        const prod = state.products.find(p => p.id === item.productId);
        if (prod) {
            prod.stock = Math.max(0, prod.stock - item.qty);
            prod.sold = (prod.sold || 0) + item.qty;
        }
    });
    saveProductsToStorage();

    // Wipe cart and clear buffer session
    state.cart = [];
    saveCartToStorage();
    updateCartBadgeCount();
    sessionStorage.removeItem("cnc_current_checkout");

    // Success notification
    showToast("Receipt submitted! Transmitted to ERPNext verification queue.", "success");
    
    // Reroute to Tracking Page
    setTimeout(() => {
        window.location.hash = "#orders";
    }, 1000);
}

// --- 8. ADMIN ACTIONS (APPROVALS, OVERRIDES) ---

// Theme Toggle Engine (Sun/Moon switch)
function initThemeEngine() {
    const themeBtn = document.getElementById("theme-btn");
    if (!themeBtn) return;

    themeBtn.addEventListener("click", () => {
        const isDark = document.body.classList.toggle("dark-theme");
        state.theme = isDark ? "dark" : "light";
        localStorage.setItem("cnc_theme", state.theme);
        
        // Update display iconography
        const sun = themeBtn.querySelector(".icon-sun");
        const moon = themeBtn.querySelector(".icon-moon");
        if (isDark) {
            if (sun) sun.style.display = "none";
            if (moon) moon.style.display = "block";
        } else {
            if (sun) sun.style.display = "block";
            if (moon) moon.style.display = "none";
        }

        // Re-draw toolpath canvas grid to match contrast
        const canvas = document.getElementById("toolpath-canvas");
        if (canvas) {
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    });
}

function initViewToggle() {
    const gridBtn = document.getElementById("grid-toggle-btn");
    const listBtn = document.getElementById("list-toggle-btn");
    const toggleContainer = document.getElementById("catalog-view-toggle");
    
    if (!gridBtn || !listBtn || !toggleContainer) return;
    
    // Sync buttons UI classes with current state on startup
    if (state.catalogViewMode === "list") {
        gridBtn.classList.remove("active");
        listBtn.classList.add("active");
        toggleContainer.classList.add("list-active");
    } else {
        gridBtn.classList.add("active");
        listBtn.classList.remove("active");
        toggleContainer.classList.remove("list-active");
    }
    
    gridBtn.addEventListener("click", () => {
        if (state.catalogViewMode === "grid") return;
        state.catalogViewMode = "grid";
        localStorage.setItem("cnc_catalog_view_mode", "grid");
        
        gridBtn.classList.add("active");
        listBtn.classList.remove("active");
        toggleContainer.classList.remove("list-active");
        
        filterAndRenderCatalog();
    });
    
    listBtn.addEventListener("click", () => {
        if (state.catalogViewMode === "list") return;
        state.catalogViewMode = "list";
        localStorage.setItem("cnc_catalog_view_mode", "list");
        
        gridBtn.classList.remove("active");
        listBtn.classList.add("active");
        toggleContainer.classList.add("list-active");
        
        filterAndRenderCatalog();
    });
}

function initAdminTabs() {
    const links = document.querySelectorAll(".admin-menu-link");
    links.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const tab = link.getAttribute("data-tab");
            state.activeAdminTab = tab;
            renderAdminView();
        });
    });

    const syncBtn = document.getElementById("sync-erpnext-btn");
    if (syncBtn) {
        syncBtn.addEventListener("click", () => {
            showToast("Querying ERPNext server api...", "info");
            syncBtn.classList.add("disabled");
            
            setTimeout(() => {
                // Sync simulation: Reload base seed levels but keep custom changes
                showToast("Synchronization complete. 5 components matched successfully.", "success");
                syncBtn.classList.remove("disabled");
                renderAdminInventory();
            }, 1200);
        });
    }
}

// Admin override inventory levels
window.overrideInventoryStock = function(productId, value) {
    const val = parseInt(value);
    if (isNaN(val) || val < 0) return;

    const prod = state.products.find(p => p.id === productId);
    if (prod) {
        prod.stock = val;
        saveProductsToStorage();
        showToast(`Stock updated for ${prod.id}. ERPNext synced.`, "success");
        renderAdminInventory();
    }
};

// Admin approves wire transfer manually
window.approveOrderPayment = function(orderId) {
    const order = state.orders.find(o => o.id === orderId);
    if (order) {
        order.status = "paid";
        saveOrdersToStorage();
        showToast(`Order #${orderId} verified. Status updated to: Paid.`, "success");
        
        // Auto transition status triggers simulation: 
        // 1. Shipped in 10 seconds
        // 2. Delivered in 25 seconds
        simulateOrderShipmentStages(orderId);

        renderAdminOrdersApproval();
    }
};

function simulateOrderShipmentStages(orderId) {
    setTimeout(() => {
        const o = state.orders.find(ord => ord.id === orderId);
        if (o && o.status === "paid") {
            o.status = "shipped";
            saveOrdersToStorage();
            showToast(`Telemetry: Order #${orderId} dispatched from Cargo Depot.`, "info");
            
            setTimeout(() => {
                const od = state.orders.find(ord => ord.id === orderId);
                if (od && od.status === "shipped") {
                    od.status = "delivered";
                    saveOrdersToStorage();
                    showToast(`Telemetry: Order #${orderId} delivered at target site.`, "success");
                }
            }, 15000);
        }
    }, 10000);
}

// Admin rejects receipt
window.rejectOrderPayment = function(orderId) {
    const confirm = window.confirm(`Reject payment wire confirmation for Order #${orderId}?`);
    if (!confirm) return;

    // Refund stock to inventory
    const order = state.orders.find(o => o.id === orderId);
    if (order) {
        order.items.forEach(item => {
            const p = state.products.find(prod => prod.id === item.productId);
            if (p) p.stock += item.qty;
        });
        saveProductsToStorage();

        // Delete order
        state.orders = state.orders.filter(o => o.id !== orderId);
        saveOrdersToStorage();
        
        showToast(`Order #${orderId} cancelled. Catalog quantities reverted.`, "info");
        renderAdminOrdersApproval();
    }
};

// --- 8b. HERO SLIDESHOW LOGIC & MANAGER ---
let slideshowTimer = null;
let currentSlideIndex = 0;
let pendingSlideImageFile = null;

function renderHeroSlides() {
    const wrapper = document.getElementById("hero-slides-wrapper");
    const dotsContainer = document.getElementById("hero-slide-dots");
    if (!wrapper || !dotsContainer) return;

    // Clear active intervals from existing slide elements before destroying them
    const existingTitles = wrapper.querySelectorAll(".hero-title");
    existingTitles.forEach(titleEl => {
        if (titleEl.typingInterval) {
            clearInterval(titleEl.typingInterval);
            titleEl.typingInterval = null;
        }
    });

    wrapper.innerHTML = "";
    dotsContainer.innerHTML = "";

    if (state.slides.length === 0) {
        const subtitleHTML = "No active slideshow slides configured. Create them inside the admin customizer tab."
            .split(" ")
            .map((w, i) => `<span class="reveal-word" style="animation-delay: ${i * 0.04}s">${w}</span>`)
            .join(" ");

        wrapper.innerHTML = `
            <div class="hero-slide active">
                <div class="hero-slide-bg" style="background-image: url('assets/images/cnc_spindle_motor.jpg');"></div>
                <div class="hero-slide-content">
                    <span class="hero-eyebrow">CNCLeaders Machinery</span>
                    <h1 class="hero-title" data-title="Industrial Machinery Platform"></h1>
                    <p class="hero-subtitle">${subtitleHTML}</p>
                </div>
            </div>
        `;
        const activeSlide = wrapper.querySelector(".hero-slide.active");
        if (activeSlide) {
            triggerTypewriterForSlide(activeSlide);
        }
        return;
    }

    if (currentSlideIndex >= state.slides.length) {
        currentSlideIndex = 0;
    }

    state.slides.forEach((slide, idx) => {
        const slideDiv = document.createElement("div");
        slideDiv.className = `hero-slide ${idx === currentSlideIndex ? 'active' : ''}`;
        
        const subtitleHTML = slide.subtitle 
            ? slide.subtitle.split(" ").map((word, wordIdx) => {
                return `<span class="reveal-word" style="animation-delay: ${wordIdx * 0.04}s">${word}</span>`;
            }).join(" ")
            : "";

        slideDiv.innerHTML = `
            <div class="hero-slide-bg" style="background-image: url('${slide.image}');"></div>
            <div class="hero-slide-content">
                <span class="hero-eyebrow">${slide.eyebrow}</span>
                <h1 class="hero-title" data-title="${slide.title.replace(/"/g, '&quot;')}"></h1>
                <p class="hero-subtitle">${subtitleHTML}</p>
                <div class="hero-actions">
                    <a href="${slide.link || '#catalog'}" class="btn btn-primary">Inspect Details</a>
                    <a href="#catalog" class="btn btn-secondary">Browse All Catalog</a>
                </div>
            </div>
        `;
        wrapper.appendChild(slideDiv);

        // Add dot indicator
        const dot = document.createElement("button");
        dot.className = `slide-dot ${idx === currentSlideIndex ? 'active' : ''}`;
        dot.addEventListener("click", () => {
            goToSlide(idx);
        });
        dotsContainer.appendChild(dot);
    });

    // Trigger typewriter for the currently active slide
    const activeSlide = wrapper.querySelector(".hero-slide.active");
    if (activeSlide) {
        triggerTypewriterForSlide(activeSlide);
    }
}

function triggerTypewriterForSlide(slide) {
    const titleEl = slide.querySelector(".hero-title");
    if (!titleEl) return;
    const fullText = titleEl.getAttribute("data-title") || titleEl.textContent;
    if (!fullText) return;
    
    // Check if we are already typing this exact text on this element to avoid restarts
    if (titleEl.getAttribute("data-currently-typing") === fullText) {
        return;
    }
    
    // Clear any existing typing interval on this element
    if (titleEl.typingInterval) {
        clearInterval(titleEl.typingInterval);
    }
    
    titleEl.setAttribute("data-currently-typing", fullText);
    titleEl.innerHTML = '';
    
    // Create cursor element
    const cursor = document.createElement("span");
    cursor.className = "typewriter-cursor";
    cursor.innerHTML = "|";
    titleEl.appendChild(cursor);
    
    let charIndex = 0;
    const speed = 25; // ms per character
    
    titleEl.typingInterval = setInterval(() => {
        if (charIndex < fullText.length) {
            const charNode = document.createTextNode(fullText.charAt(charIndex));
            titleEl.insertBefore(charNode, cursor);
            charIndex++;
        } else {
            clearInterval(titleEl.typingInterval);
            titleEl.typingInterval = null;
            setTimeout(() => {
                if (cursor.parentNode === titleEl) {
                    cursor.classList.add("finished");
                }
            }, 1000);
        }
    }, speed);
}

function clearTypewriterForSlide(slide) {
    const titleEl = slide.querySelector(".hero-title");
    if (!titleEl) return;
    if (titleEl.typingInterval) {
        clearInterval(titleEl.typingInterval);
        titleEl.typingInterval = null;
    }
    titleEl.removeAttribute("data-currently-typing");
    titleEl.textContent = "";
}

function goToSlide(index) {
    if (state.slides.length <= 1) {
        const activeSlide = document.querySelector(".hero-slide.active");
        if (activeSlide) {
            triggerTypewriterForSlide(activeSlide);
        }
        return;
    }
    
    if (index < 0) index = state.slides.length - 1;
    if (index >= state.slides.length) index = 0;
    
    currentSlideIndex = index;
    
    const slides = document.querySelectorAll(".hero-slide");
    const dots = document.querySelectorAll(".slide-dot");
    
    slides.forEach((slide, idx) => {
        if (idx === currentSlideIndex) {
            slide.classList.add("active");
            triggerTypewriterForSlide(slide);
        } else {
            slide.classList.remove("active");
            clearTypewriterForSlide(slide);
        }
    });

    dots.forEach((dot, idx) => {
        if (idx === currentSlideIndex) {
            dot.classList.add("active");
        } else {
            dot.classList.remove("active");
        }
    });
}

function startSlideshowRotation() {
    stopSlideshowRotation();
    if (state.slides.length <= 1) return;
    slideshowTimer = setInterval(() => {
        goToSlide(currentSlideIndex + 1);
    }, 4000);
}

function stopSlideshowRotation() {
    if (slideshowTimer) {
        clearInterval(slideshowTimer);
        slideshowTimer = null;
    }
}

// Custom select image file helper
window.toggleCustomSlideImageUpload = function(val) {
    const customGroup = document.getElementById("slide-custom-upload-group");
    if (!customGroup) return;
    
    if (val === "custom") {
        customGroup.style.display = "block";
    } else {
        customGroup.style.display = "none";
        resetSlideUploadZone();
    }
};

function resetSlideUploadZone() {
    pendingSlideImageFile = null;
    const previewArea = document.getElementById("slide-upload-preview");
    if (previewArea) previewArea.style.display = "none";
}

function initSlideCustomizerForm() {
    const form = document.getElementById("admin-add-slide-form");
    const dropZone = document.getElementById("slide-upload-zone");
    const fileInput = document.getElementById("slide-file-input");
    const removeBtn = document.getElementById("remove-slide-img-btn");

    if (!form) return;

    if (dropZone && fileInput) {
        dropZone.addEventListener("click", () => {
            if (!pendingSlideImageFile) {
                fileInput.click();
            }
        });

        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.classList.add("hover");
        });

        dropZone.addEventListener("dragleave", () => {
            dropZone.classList.remove("hover");
        });

        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("hover");
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleSlideFile(files[0]);
            }
        });

        fileInput.addEventListener("change", (e) => {
            const files = e.target.files;
            if (files.length > 0) {
                handleSlideFile(files[0]);
            }
        });
    }

    if (removeBtn) {
        removeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            resetSlideUploadZone();
        });
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        
        const eyebrow = document.getElementById("slide-eyebrow").value;
        const title = document.getElementById("slide-title").value;
        const subtitle = document.getElementById("slide-subtitle").value;
        const link = document.getElementById("slide-link").value || "#catalog";
        const imgSelect = document.getElementById("slide-image-select").value;

        let imageSrc = imgSelect;
        
        if (imgSelect === "custom") {
            if (!pendingSlideImageFile) {
                showToast("Please upload a custom slide image screenshot first.", "info");
                return;
            }
            const previewImg = document.getElementById("slide-preview-img");
            imageSrc = previewImg ? previewImg.src : "";
        }

        const newSlide = {
            eyebrow: eyebrow.toUpperCase(),
            title: title,
            subtitle: subtitle,
            link: link,
            image: imageSrc
        };

        state.slides.push(newSlide);
        saveSlidesToStorage();
        showToast("Dynamic slide successfully injected to live carousel.", "success");
        
        form.reset();
        resetSlideUploadZone();
        document.getElementById("slide-custom-upload-group").style.display = "none";
        
        renderAdminSlideshowTable();
        renderHeroSlides();
        goToSlide(state.slides.length - 1);
    });
}

function handleSlideFile(file) {
    if (!file.type.match("image.*")) {
        showToast("Error: Upload must be a valid image file.", "info");
        return;
    }

    pendingSlideImageFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        const previewImg = document.getElementById("slide-preview-img");
        const previewArea = document.getElementById("slide-upload-preview");
        const fileNameLabel = document.getElementById("slide-file-name");

        if (previewImg) previewImg.src = e.target.result;
        if (previewArea) previewArea.style.display = "flex";
        if (fileNameLabel) fileNameLabel.innerText = file.name;
    };
    reader.readAsDataURL(file);
}

function renderAdminSlideshowTable() {
    const tableBody = document.getElementById("admin-slides-rows");
    if (!tableBody) return;

    tableBody.innerHTML = "";

    if (state.slides.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align:center; padding: 48px; color:var(--text-muted);">
                    Carousel is empty. Home view will display default warning panels.
                </td>
            </tr>
        `;
        return;
    }

    state.slides.forEach((slide, idx) => {
        const tr = document.createElement("tr");
        
        // Define disable classes for boundaries
        const upDisabled = idx === 0 ? "disabled" : "";
        const downDisabled = idx === state.slides.length - 1 ? "disabled" : "";

        tr.innerHTML = `
            <td><code style="font-weight:bold; font-size:1.1rem; color:var(--primary-blue);">#${idx + 1}</code></td>
            <td>
                <img src="${slide.image}" alt="Slide Thumb" class="admin-img-thumb" style="width:80px; height:45px; border-radius:4px;">
            </td>
            <td>
                <div style="font-weight:700; font-size:0.95rem;">${slide.title}</div>
                <div style="font-size:0.75rem; color:var(--primary-blue); text-transform:uppercase; letter-spacing:1px; margin-top:2px;">${slide.eyebrow}</div>
                <div style="font-size:0.8rem; color:var(--text-muted); max-width:400px; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${slide.subtitle}</div>
            </td>
            <td>
                <div class="order-actions-flex">
                    <button class="sort-arrow-btn ${upDisabled}" onclick="moveSlide(${idx}, -1)" title="Move Slide Up" ${idx === 0 ? 'disabled' : ''}>
                        <i data-lucide="arrow-up" style="width:14px; height:14px;"></i>
                    </button>
                    <button class="sort-arrow-btn ${downDisabled}" onclick="moveSlide(${idx}, 1)" title="Move Slide Down" ${idx === state.slides.length - 1 ? 'disabled' : ''}>
                        <i data-lucide="arrow-down" style="width:14px; height:14px;"></i>
                    </button>
                </div>
            </td>
            <td><code>${slide.link || '#catalog'}</code></td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="deleteSlide(${idx})" style="color:#EF4444; border-color:#EF4444; padding:6px 10px;">
                    <i data-lucide="trash-2" style="width:14px; height:14px; display:inline-block; vertical-align:middle; margin-right:4px;"></i> Delete
                </button>
            </td>
        `;
        tableBody.appendChild(tr);
    });

    lucide.createIcons();
}

window.moveSlide = function(index, direction) {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= state.slides.length) return;

    // Swap index elements in slides state array
    const temp = state.slides[index];
    state.slides[index] = state.slides[targetIndex];
    state.slides[targetIndex] = temp;

    saveSlidesToStorage();
    showToast("Slideshow sequence reordered.", "success");

    renderAdminSlideshowTable();
    renderHeroSlides();
    goToSlide(targetIndex);
};

window.deleteSlide = function(index) {
    const confirmDelete = window.confirm(`Permanently remove Carousel Slide #${index + 1}?`);
    if (!confirmDelete) return;

    state.slides.splice(index, 1);
    saveSlidesToStorage();
    showToast("Slide deleted successfully.", "info");

    renderAdminSlideshowTable();
    renderHeroSlides();
    goToSlide(0);
};

// --- 8c. DYNAMIC FOOTER TELEMETRY TICKER ---
function initFooterTicker() {
    const tickerSequence = document.querySelector(".ticker-sequence");
    if (!tickerSequence) return;
    
    setInterval(() => {
        const x = (100 + Math.random() * 150).toFixed(2);
        const y = (50 + Math.random() * 100).toFixed(2);
        const z = (-1 - Math.random() * 3).toFixed(2);
        const f = (1200 + Math.floor(Math.random() * 800));
        const commands = ["G01", "G02", "G03"];
        const randomCommand = commands[Math.floor(Math.random() * commands.length)];
        
        let subCommand = "";
        if (randomCommand !== "G01") {
            subCommand = ` I${(Math.random() * 10).toFixed(1)} J${(Math.random() * 10).toFixed(1)}`;
        }
        
        tickerSequence.innerText = `${randomCommand} X${x} Y${y} Z${z}${subCommand} F${f} ; Telemetry feed active`;
    }, 3000);
}

// --- MOBILE MENU INIT ---
function initMobileMenu() {
    const mobileBtn = document.getElementById("mobile-menu-btn");
    const navLinks = document.querySelector(".nav-links");
    
    if (mobileBtn && navLinks) {
        mobileBtn.addEventListener("click", () => {
            const isActive = navLinks.classList.toggle("mobile-active");
            const iconMenu = mobileBtn.querySelector(".icon-menu");
            const iconX = mobileBtn.querySelector(".icon-x");
            
            if (isActive) {
                if(iconMenu) iconMenu.style.display = "none";
                if(iconX) iconX.style.display = "block";
            } else {
                if(iconMenu) iconMenu.style.display = "block";
                if(iconX) iconX.style.display = "none";
            }
        });
        
        // Auto-close on link click
        navLinks.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                navLinks.classList.remove("mobile-active");
                const iconMenu = mobileBtn.querySelector(".icon-menu");
                const iconX = mobileBtn.querySelector(".icon-x");
                if(iconMenu) iconMenu.style.display = "block";
                if(iconX) iconX.style.display = "none";
            });
        });
    }
}

// --- LANGUAGE TOGGLE INIT ---
function initLanguageToggle() {
    const langBtn = document.getElementById("lang-btn");
    if(langBtn) {
        langBtn.addEventListener("click", () => {
            const newLang = state.lang === 'en' ? 'ar' : 'en';
            applyLanguage(newLang);
        });
    }
}

// --- 9. APP LIFECYCLE INITIALIZER ---
document.addEventListener("DOMContentLoaded", () => {
    // 1. Setup local storage states
    initializeState();

    // 2. Init Interactive Toolpath Header Canvas
    initToolpathCanvas();

    // 3. Init Navigation Router & Hash Listener
    window.addEventListener("hashchange", handleNavigation);
    handleNavigation(); // Trigger initial routing match

    // 4. Init Event Handlers
    initCartDrawer();
    initCheckoutForm();
    initPaymentSlipUpload();
    initThemeEngine();
    initLanguageToggle();
    initMobileMenu();
    initViewToggle();
    initAdminTabs();
    initSlideCustomizerForm();
    initFooterTicker();

    // 5. Init Slideshow Hover Pause
    const sliderContainer = document.getElementById("hero-slider-container");
    if (sliderContainer) {
        sliderContainer.addEventListener("mouseenter", stopSlideshowRotation);
        sliderContainer.addEventListener("mouseleave", startSlideshowRotation);
    }

    // Initial cart drawer visual numbers sync
    updateCartBadgeCount();
    
    // Global loader fade-out placeholder
    console.log("CNCLeaders Machinery Catalog application successfully calibrated and synced.");
});

// --- Category Carousel Scroll Logic ---
window.scrollCategoryCarousel = function(categoryId, direction) {
    const track = document.getElementById('carousel-track-' + categoryId);
    if (track) {
        const scrollAmount = track.clientWidth > 600 ? 600 : track.clientWidth * 0.8;
        track.scrollBy({ left: direction * scrollAmount, behavior: 'smooth' });
    }
};
