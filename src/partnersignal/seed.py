"""Deterministic, fictional demo data.

Every company, person, e-mail address and number below is invented. Dates are stored as
offsets from the day the database is seeded, so the demo always shows a live-looking
week: follow-ups due today, a few overdue, deadlines approaching.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from . import clock
from .catalog import SERVICES_BY_KEY, inline
from .db import Base
from .models import Activity, Draft, Opportunity, Partner, Signal, Specialist

SPECIALISTS = [
    ("sp-rao", "Priya Rao", "Security Solutions Architect", "security", 6),
    ("sp-okafor", "Daniel Okafor", "Security Consultant", "security", 5),
    ("sp-leblanc", "Julie Leblanc", "Cloud & Hybrid IT Architect", "cloud", 6),
    ("sp-nguyen", "Kevin Nguyen", "Migration Engineer", "cloud", 5),
    ("sp-haddad", "Omar Haddad", "Networking Practice Lead", "network", 6),
    ("sp-silva", "Ana Silva", "AI Solutions Specialist", "ai", 5),
    ("sp-kowalski", "Marta Kowalski", "Lifecycle Services Manager", "lifecycle", 7),
    ("sp-grant", "Tessa Grant", "Enablement & Training Lead", "training", 8),
]

SPECIALIST_NAMES = {row[0]: row[1] for row in SPECIALISTS}

# fmt: off
# id, name, type, tier, city, province, verticals, vendors, contact, title,
# trailing revenue, services revenue, product mix, services used, about
PARTNERS = [
    ("northstar", "Northstar IT Group", "Managed service provider", "Gold", "Mississauga", "ON",
     ["Healthcare", "Professional services"], ["Microsoft", "Fortinet", "Dell"], "Maya Chen",
     "Director of Client Services", 4_800_000, 310_000,
     {"security": .31, "cloud": .24, "network": .14, "lifecycle": .23, "ai": .08}, ["cloud"],
     "Runs a 24-person MSP with a growing clinic and dental portfolio across the GTA."),
    ("harbour", "Harbour Tech Solutions", "Value-added reseller", "Gold", "Burnaby", "BC",
     ["Manufacturing", "Logistics"], ["HPE", "VMware", "Microsoft"], "Jordan Patel", "VP, Sales", 7_200_000,
     520_000, {"cloud": .38, "network": .19, "lifecycle": .27, "security": .16}, ["network", "lifecycle"],
     "Mid-market VAR with a strong manufacturing base in the Lower Mainland."),
    ("prairie", "Prairie Digital Partners", "Regional reseller", "Silver", "Saskatoon", "SK",
     ["Distribution", "Agriculture"], ["Cisco", "Lenovo"], "Avery Thompson", "Account Executive", 2_100_000, 64000,
     {"network": .44, "lifecycle": .36, "security": .12, "cloud": .08}, [],
     "Product-led reseller starting to build a services line with two engineers."),
    ("cobalt", "Cobalt Cloud Advisors", "Cloud consultancy", "Gold", "Montréal", "QC",
     ["Financial services", "Insurance"], ["Microsoft", "AWS"], "Samira Ali", "Managing Partner", 3_400_000,
     880_000, {"cloud": .52, "ai": .28, "security": .2}, ["cloud", "security"],
     "Boutique Azure partner serving regional credit unions and insurers."),
    ("summit", "Summit Works", "Technology retailer", "Registered", "Calgary", "AB", ["Retail", "SMB"],
     ["HP", "Microsoft"], "Ethan Martin", "Owner", 1_300_000, 21000,
     {"lifecycle": .61, "cloud": .22, "security": .17}, [],
     "Retail storefront plus a small business-IT team; wants to sell more services."),
    ("vectorlink", "VectorLink Networks", "Network integrator", "Gold", "Halifax", "NS",
     ["Public sector", "Education"], ["Cisco", "Palo Alto Networks"], "Noah Williams", "Solutions Director",
     5_900_000, 740_000, {"network": .57, "security": .33, "cloud": .1}, ["network"],
     "Integrator with provincial and municipal contracts across Atlantic Canada."),
    ("maple", "Maple Ridge Systems", "Managed service provider", "Silver", "Ottawa", "ON", ["Non-profit", "Legal"],
     ["Microsoft", "Sophos", "Lenovo"], "Chloé Bernard", "Service Delivery Manager", 1_900_000, 150_000,
     {"security": .29, "cloud": .33, "ai": .12, "lifecycle": .26}, ["security"],
     "MSP for law firms and national charities headquartered in Ottawa."),
    ("borealis", "Borealis Integration", "Systems integrator", "Gold", "Edmonton", "AB", ["Energy", "Utilities"],
     ["Cisco", "Dell", "VMware"], "Liam O'Connor", "Practice Manager", 8_600_000, 1_100_000,
     {"network": .31, "cloud": .34, "security": .22, "lifecycle": .13}, ["network", "cloud"],
     "Integrator with OT and field-site experience in oil, gas and utilities."),
    ("lakeshore", "Lakeshore Tech", "Value-added reseller", "Silver", "Kingston", "ON", ["Education", "Healthcare"],
     ["HP", "Aruba", "Microsoft"], "Grace Kim", "Sales Manager", 2_700_000, 95000,
     {"lifecycle": .42, "network": .3, "cloud": .18, "security": .1}, ["lifecycle"],
     "Supplies school boards and a regional hospital network in eastern Ontario."),
    ("pacifica", "Pacifica Data", "Managed service provider", "Silver", "Victoria", "BC", ["Government", "Tourism"],
     ["Microsoft", "Veeam"], "Marcus Lee", "CTO", 1_600_000, 240_000, {"cloud": .46, "security": .34, "ai": .2},
     ["cloud"], "Cloud-first MSP; recently won two municipal clients."),
    ("stlaurent", "Groupe St-Laurent TI", "Value-added reseller", "Gold", "Québec City", "QC",
     ["Manufacturing", "Public sector"], ["Lenovo", "Cisco", "Microsoft"], "Mathieu Gagnon", "Directeur des ventes",
     6_100_000, 290_000, {"lifecycle": .35, "network": .25, "cloud": .22, "security": .18}, ["lifecycle"],
     "Bilingual VAR with large device-refresh programs for manufacturers."),
    ("ironwood", "Ironwood Secure", "Security specialist", "Silver", "Waterloo", "ON",
     ["Technology", "Financial services"], ["Palo Alto Networks", "CrowdStrike"], "Hannah Wright",
     "Head of Partnerships", 2_300_000, 410_000, {"security": .78, "cloud": .22}, ["security"],
     "Security-focused reseller with a strong SOC 2 practice for software firms."),
    ("tidewater", "Tidewater Computing", "Regional reseller", "Registered", "Moncton", "NB", ["SMB", "Municipal"],
     ["Dell", "Microsoft"], "Olivia Martin", "Account Manager", 900_000, 12000,
     {"lifecycle": .55, "cloud": .25, "security": .2}, [], "Small reseller growing through municipal and SMB work."),
    ("granite", "Granite Peak IT", "Managed service provider", "Gold", "Vancouver", "BC",
     ["Professional services", "Real estate"], ["Microsoft", "Fortinet", "HP"], "Ryan Brooks", "COO", 3_900_000,
     620_000, {"cloud": .33, "security": .27, "ai": .21, "lifecycle": .19}, ["cloud", "security"],
     "Fast-growing MSP; leadership wants an AI offer in market by next fiscal year."),
    ("redriver", "Red River Solutions", "Value-added reseller", "Silver", "Winnipeg", "MB",
     ["Agriculture", "Transportation"], ["HPE", "Aruba"], "Sofia Rossi", "Business Development Manager", 2_400_000,
     88000, {"network": .39, "cloud": .31, "lifecycle": .3}, ["network"],
     "Serves co-operatives and trucking firms across Manitoba."),
    ("keystone", "Keystone Learning Tech", "Education solutions partner", "Silver", "London", "ON", ["Education"],
     ["Lenovo", "Microsoft", "Google"], "Ben Carter", "Education Lead", 3_100_000, 70000,
     {"lifecycle": .58, "network": .22, "ai": .2}, [], "Specialist in K-12 and college device programs."),
    ("aurora", "Aurora Networks North", "Network integrator", "Registered", "Sudbury", "ON",
     ["Mining", "Public sector"], ["Cisco", "Fortinet"], "Isabelle Roy", "President", 1_700_000, 130_000,
     {"network": .62, "security": .28, "lifecycle": .1}, ["network"],
     "Integrator for northern Ontario mining sites and municipalities."),
    ("clearpath", "ClearPath Consulting", "Microsoft solutions partner", "Gold", "Toronto", "ON",
     ["Professional services", "Legal", "Finance"], ["Microsoft"], "Arjun Mehta", "Partner, Modern Work", 4_200_000,
     960_000, {"cloud": .4, "ai": .38, "security": .22}, ["cloud", "ai"],
     "Modern Work partner with dozens of Copilot pilots in the pipeline."),
]

# partner, kind, source, practice, service, title, detail, strength, detected offset, deadline offset
SIGNALS = [
    ("northstar", "renewal", "Renewal calendar", "security", "sec-ransomware",
     "Firewall subscriptions renewing for 11 clinic customers",
     "Fortinet bundle renewals for 11 end customers fall inside 60 days. No security assessment has been attached to these accounts in the last 24 months.",
     5, -3, 52),
    ("northstar", "end_of_support", "Install-base data", "lifecycle", "life-eos",
     "38 Windows Server 2016 hosts approaching end of extended support",
     "Distribution records show 38 server licences sold 2017-2019 across 9 customers.", 4, -6, "ws2016"),
    ("harbour", "vendor_program", "Vendor program update", "cloud", "cloud-vmware",
     "Virtualization renewals for 6 manufacturing customers",
     "Six end customers renew virtualization subscriptions this quarter under the new per-core licensing.", 5, -2,
     75),
    ("harbour", "purchase", "Distribution orders", "network", "net-sdwan",
     "Branch router order for 14 sites with no deployment services",
     "A 14-site edge router order shipped last week; no staging or SD-WAN design services were quoted.", 3, -8, None),
    ("prairie", "purchase", "Distribution orders", "network", "net-assessment",
     "Wireless access points ordered for two new warehouse sites",
     "62 access points ordered for a customer opening two sites. No site survey was quoted.", 4, -4, 40),
    ("prairie", "attach_gap", "Whitespace analysis", "lifecycle", "life-deploy",
     "Device revenue with no deployment services attached",
     "36% of Prairie's product revenue is end-user devices; they have never used deployment services.", 3, -10, None),
    ("cobalt", "inbound", "Marketing engagement", "ai", "ai-governance",
     "Attended the 'AI without data leaks' webinar and downloaded the checklist",
     "Samira attended the full session and asked a question about labelling client data.", 4, -1, None),
    ("summit", "attach_gap", "Whitespace analysis", "training", "train-sales",
     "Services attach rate of 1.6% vs. 9% peer benchmark",
     "Summit sells devices and licences but rarely attaches services; its sales team has no discovery training.", 3,
     -12, None),
    ("vectorlink", "renewal", "Contract calendar", "network", "net-segmentation",
     "Provincial remote-access program starts next quarter",
     "Public-sector customer announced a remote-access program; tender requires a segmentation design.", 5, -5, 88),
    ("maple", "marketplace", "Cloud marketplace", "ai", "ai-copilot",
     "Copilot seats tripled in 60 days across 4 law-firm tenants",
     "Seat growth without an adoption plan often stalls; permission clean-up is usually the first need.", 4, -2,
     None),
    ("maple", "renewal", "Renewal calendar", "security", "sec-posture",
     "Cyber-insurance renewals for 3 legal clients",
     "Insurers now ask for MFA, EDR and tested backups evidence. Renewals are 30-45 days out.", 4, -7, 38),
    ("borealis", "end_of_support", "Install-base data", "network", "net-assessment",
     "Core switching at 5 field sites past end of sale",
     "Switch models purchased in 2016 reached end of sale; support contracts lapse in 5 months.", 4, -9, 150),
    ("lakeshore", "purchase", "Distribution orders", "lifecycle", "life-deploy",
     "1,200 Chromebooks ordered for a school board refresh",
     "Large education refresh shipping in waves; imaging and asset tagging are not quoted.", 5, -2, 30),
    ("lakeshore", "purchase", "Distribution orders", "lifecycle", "life-itad",
     "Retired laptops from the same school-board refresh",
     "The previous device generation (~1,100 units) will need certified data destruction.", 3, -2, 60),
    ("pacifica", "inbound", "Marketing engagement", "security", "sec-ransomware",
     "Requested a ransomware tabletop for a municipal client",
     "Form fill from the partner portal, flagged by the municipal client's council.", 4, -1, None),
    ("stlaurent", "end_of_support", "Install-base data", "lifecycle", "life-eos",
     "54 Windows Server 2016 hosts across manufacturing customers",
     "Several hosts run plant-floor applications; migration windows need planning.", 4, -11, "ws2016"),
    ("ironwood", "attach_gap", "Whitespace analysis", "cloud", "cloud-readiness",
     "Security-only partner whose customers are moving to cloud",
     "22% of Ironwood's revenue is cloud security; they have no migration capability of their own.", 3, -14, None),
    ("tidewater", "purchase", "Distribution orders", "cloud", "cloud-migration",
     "Municipal customer bought Azure credits and a single server",
     "Small but unusual order pattern suggesting a hybrid move; partner has no cloud engineers.", 2, -5, None),
    ("granite", "inbound", "Account manager referral", "ai", "ai-readiness",
     "COO asked their account manager for an AI offer they can resell",
     "Granite wants a packaged AI readiness offer for professional-services clients.", 5, -3, None),
    ("redriver", "vendor_program", "Vendor program update", "cloud", "cloud-vmware",
     "Two co-op customers facing virtualization licensing increases",
     "Renewal quotes rose significantly under per-core licensing; customers asked about alternatives.", 3, -6, 95),
    ("keystone", "attach_gap", "Whitespace analysis", "network", "net-assessment",
     "Device programs growing but classroom Wi-Fi never assessed",
     "Keystone's device volume grew 40% while network services stayed at zero.", 3, -9, None),
    ("aurora", "purchase", "Distribution orders", "security", "sec-posture",
     "Firewall purchase for a mining site after an incident",
     "Emergency firewall order with expedited shipping; the note mentions a recent phishing incident.", 4, -3, None),
    ("clearpath", "marketplace", "Cloud marketplace", "ai", "ai-governance",
     "Copilot pilots at 5 customers blocked on sensitive-data labelling",
     "ClearPath asked for help with data classification before pilots can widen.", 4, -4, None),
    ("harbour", "end_of_support", "Install-base data", "lifecycle", "life-eos",
     "21 Windows Server 2016 hosts at three manufacturing customers",
     "Server licences sold in 2018 with no migration services attached since.", 3, -1, "ws2016"),
    ("cobalt", "marketplace", "Cloud marketplace", "security", "sec-mdr",
     "Defender licences upgraded at 4 credit unions without a monitoring service",
     "Customers moved to premium security licences, but alerts are not monitored after hours.", 4, -2, None),
    ("vectorlink", "purchase", "Distribution orders", "security", "sec-posture",
     "Next-generation firewall order for a school district",
     "Twelve firewalls ordered for a district-wide rollout; no configuration review quoted.", 3, -1, None),
    ("granite", "renewal", "Renewal calendar", "security", "sec-ransomware",
     "Backup subscriptions renewing at 7 real-estate customers",
     "Renewals are a natural moment to test restores and document recovery times.", 3, -4, 34),
    ("pacifica", "marketplace", "Cloud marketplace", "ai", "ai-readiness",
     "Municipal client added Azure OpenAI to its subscription",
     "Consumption started last week; the client has no AI usage policy yet.", 4, 0, None),
    ("ironwood", "inbound", "Marketing engagement", "training", "train-cert",
     "Three engineers registered interest in cloud security certification",
     "Registrations came through the partner portal training page.", 2, -2, None),
    ("tidewater", "attach_gap", "Whitespace analysis", "lifecycle", "life-deploy",
     "Device orders up 60% with no deployment services",
     "Tidewater ships devices direct to customers and images them by hand.", 3, -6, None),
    ("maple", "end_of_support", "Install-base data", "cloud", "cloud-migration",
     "File servers at two national charities approaching end of support",
     "Customers still store donor records on on-premises file servers.", 3, -3, "ws2016"),
    ("redriver", "purchase", "Distribution orders", "network", "net-sdwan",
     "LTE routers ordered for 30 trucks and 4 depots",
     "Unusual mobile-connectivity order; SD-WAN or managed connectivity could simplify it.", 3, -5, None),
    ("keystone", "marketplace", "Cloud marketplace", "ai", "ai-governance",
     "College customer enabled Copilot for 400 staff",
     "Student and staff data mixed in shared drives; labelling is not configured.", 4, -1, None),
    ("clearpath", "inbound", "Account manager referral", "training", "train-sales",
     "New account managers asking how to position AI services",
     "Four new sellers joined; ClearPath wants discovery training focused on AI conversations.", 3, -3, 45),
    ("aurora", "vendor_program", "Vendor program update", "network", "net-segmentation",
     "Mining customer's OT network flagged in vendor security advisory",
     "Advisory affects firmware used on site controllers; segmentation is the recommended mitigation.", 5, -1, 60),
    ("borealis", "inbound", "Account manager referral", "training", "train-cert",
     "Hiring four network engineers who need OT security certification",
     "Needed to keep a utility contract's staffing requirement.", 3, -8, 70),
]

# partner, signal index (or None), title, end customer, industry, practice, service, stage, value,
# budget, authority, need, timeline, challenge, next step, due offset, specialist, created offset,
# stage-changed offset
OPPORTUNITIES = [
    ("northstar", 0, "Ransomware readiness for clinic group", "Lakeview Family Clinics", "Healthcare", "security",
     "sec-ransomware", "Qualified", 14000, "indicated", "decision_maker", "high", "under_3_months",
     "Their backups have never been restore-tested and the insurer is asking for proof before renewal.",
     "Send scoping questionnaire and book specialist call", 0, "sp-rao", -18, -6),
    ("northstar", 1, "Server 2016 migration plan", "Harmon Dental Partners", "Healthcare", "lifecycle", "life-eos",
     "Discovery", 39000, "unknown", "influencer", "medium", "3_6_months",
     "Practice-management software runs on two old servers that nobody wants to touch.",
     "Confirm server inventory and application owners", -2, None, -9, -9),
    ("harbour", 2, "Virtualization exit assessment", "Coastline Fabrication", "Manufacturing", "cloud",
     "cloud-vmware", "Solutioning", 22000, "confirmed", "decision_maker", "high", "under_3_months",
     "Renewal quote went up sharply; CFO wants options before signing.",
     "Review licensing model with Julie before proposal", 2, "sp-leblanc", -30, -8),
    ("harbour", 3, "SD-WAN staging for 14 branches", "Pacific Freightways", "Logistics", "network", "net-sdwan",
     "Prospect", 48000, "unknown", "unknown", "medium", "unknown", "", "Call Jordan about the router order", -1,
     None, -6, -6),
    ("prairie", 4, "Warehouse Wi-Fi site survey", "Northern Grain Co-op", "Agriculture", "network",
     "net-assessment", "Discovery", 12000, "indicated", "influencer", "high", "under_3_months",
     "Handheld scanners drop connection in the cold-storage aisles and orders get mis-picked.",
     "Get site drawings and opening dates", 0, None, -12, -5),
    ("cobalt", 6, "Data governance before AI rollout", "Laurentian Credit Union", "Financial services", "ai",
     "ai-governance", "Solutioning", 17000, "indicated", "decision_maker", "high", "3_6_months",
     "Board wants AI assistants for member services but compliance will not approve until data is labelled.",
     "Specialist to draft scope; confirm OSFI guideline references", 3, "sp-silva", -21, -4),
    ("summit", 7, "Discovery skills workshop for sales team", "Summit Works (internal)", "Retail", "training",
     "train-sales", "Qualified", 6000, "confirmed", "decision_maker", "medium", "3_6_months",
     "Reps sell hardware well but freeze when a customer asks about security or cloud.",
     "Propose two dates in November", -4, "sp-grant", -26, -15),
    ("vectorlink", 8, "Segmentation design for remote-access program", "Province of NS - Dept. of Services",
     "Public sector", "network", "net-segmentation", "Proposal", 36000, "confirmed", "decision_maker", "high",
     "under_3_months", "Tender requires a segmentation design for 3,000 remote workers before go-live.",
     "Proposal review call with Noah and Omar", 1, "sp-haddad", -40, -3),
    ("maple", 9, "Copilot adoption pilot for law firm", "Delaney & Moss LLP", "Legal", "ai", "ai-copilot",
     "Discovery", 28000, "unknown", "influencer", "medium", "3_6_months",
     "Partners are paying for Copilot but associates say it surfaces documents they shouldn't see.",
     "Ask about permission clean-up and pilot group", -3, None, -8, -8),
    ("maple", 10, "Security posture review ahead of insurance renewal", "Canadian Literacy Network", "Non-profit",
     "security", "sec-posture", "Qualified", 18000, "indicated", "decision_maker", "high", "under_3_months",
     "Insurer requires evidence of MFA and EDR by renewal; premium doubles otherwise.",
     "Route to security specialist", 0, None, -14, -2),
    ("borealis", 11, "Field-site network refresh assessment", "Athabasca Midstream", "Energy", "network",
     "net-assessment", "Qualified", 12000, "indicated", "influencer", "medium", "3_6_months",
     "Five compressor sites run on switches that can no longer be supported.", "Confirm site access requirements",
     4, "sp-haddad", -19, -10),
    ("lakeshore", 12, "Chromebook imaging and deployment", "Limestone District School Board", "Education",
     "lifecycle", "life-deploy", "Proposal", 31000, "confirmed", "decision_maker", "high", "under_3_months",
     "Devices arrive before winter break; IT has three people to image 1,200 units.",
     "Send final quote and deployment schedule", -1, "sp-kowalski", -24, -5),
    ("lakeshore", 13, "Certified disposition of retired laptops", "Limestone District School Board", "Education",
     "lifecycle", "life-itad", "Prospect", 11000, "unknown", "unknown", "low", "3_6_months", "",
     "Mention ITAD during deployment call", 3, None, -2, -2),
    ("pacifica", 14, "Ransomware tabletop for municipality", "District of Saanich Ridge", "Government", "security",
     "sec-ransomware", "Discovery", 14000, "unknown", "influencer", "high", "under_3_months",
     "Council asked IT to prove it could recover from an attack like the one at a neighbouring town.",
     "Book discovery call with Marcus and IT manager", 0, None, -2, -2),
    ("stlaurent", 15, "Server end-of-support program", "Usinage Beauport", "Manufacturing", "lifecycle", "life-eos",
     "Solutioning", 39000, "indicated", "decision_maker", "high", "3_6_months",
     "Plant-floor apps run on Server 2016; downtime windows only exist over the holidays.",
     "Specialist to map migration windows", -5, "sp-kowalski", -45, -27),
    ("ironwood", 16, "Cloud readiness for SaaS customers", "Brightloop Software", "Technology", "cloud",
     "cloud-readiness", "Prospect", 16000, "unknown", "unknown", "low", "6_plus_months", "",
     "Intro email to Hannah about co-selling", 5, None, -5, -5),
    ("granite", 18, "Packaged AI readiness offer", "Granite Peak IT (resale)", "Professional services", "ai",
     "ai-readiness", "Qualified", 9500, "indicated", "decision_maker", "high", "under_3_months",
     "Leadership wants a repeatable AI workshop they can put on their price list by January.",
     "Route to AI specialist", 1, None, -7, -3),
    ("redriver", 19, "Virtualization alternatives for co-op", "Prairie Harvest Co-operative", "Agriculture",
     "cloud", "cloud-vmware", "Discovery", 22000, "unknown", "influencer", "medium", "3_6_months",
     "Renewal price increase was not in the budget; IT manager exploring alternatives.",
     "Send licensing comparison one-pager", -6, None, -20, -20),
    ("aurora", 21, "Post-incident security posture review", "Copper Cliff Mining Services", "Mining", "security",
     "sec-posture", "Qualified", 18000, "confirmed", "influencer", "high", "under_3_months",
     "A phishing email led to a compromised mailbox; the site manager wants an independent review.",
     "Specialist call to confirm scope", 2, "sp-okafor", -9, -4),
    ("clearpath", 22, "Sensitive-data labelling before Copilot", "Harbourfront Legal Group", "Legal", "ai",
     "ai-governance", "Discovery", 17000, "indicated", "influencer", "high", "3_6_months",
     "Pilot is paused because matter files are not labelled.", "Confirm tenant size and data locations", 1, None,
     -4, -4),
    ("borealis", 35, "OT security certification bootcamp", "Borealis Integration (internal)", "Energy", "training",
     "train-cert", "Discovery", 8500, "confirmed", "decision_maker", "medium", "3_6_months",
     "New hires need certification within 90 days of joining the utility contract.",
     "Send course outline and dates", -2, None, -8, -8),
    ("keystone", 20, "Classroom Wi-Fi assessment", "Thames Valley Catholic Schools", "Education", "network",
     "net-assessment", "Prospect", 12000, "unknown", "unknown", "unknown", "unknown", "",
     "Share whitespace data with Ben", 0, None, -3, -3),
    # Closed history for reporting.
    ("northstar", None, "Microsoft 365 tenant migration", "Bayview Physiotherapy", "Healthcare", "cloud",
     "cloud-migration", "Won", 41000, "confirmed", "decision_maker", "high", "under_3_months",
     "Consolidating two tenants after an acquisition.", "", None, "sp-nguyen", -110, -38),
    ("harbour", None, "Security posture assessment", "Coastline Fabrication", "Manufacturing", "security",
     "sec-posture", "Won", 18000, "confirmed", "decision_maker", "high", "3_6_months", "Customer audit finding.",
     "", None, "sp-rao", -95, -52),
    ("vectorlink", None, "Campus network assessment", "Dalhousie Research Park", "Education", "network",
     "net-assessment", "Won", 12000, "confirmed", "decision_maker", "medium", "3_6_months",
     "Wireless dead zones in new lab building.", "", None, "sp-haddad", -80, -30),
    ("cobalt", None, "AI readiness workshop", "St-Denis Assurance", "Insurance", "ai", "ai-readiness", "Won", 9500,
     "confirmed", "decision_maker", "medium", "under_3_months", "Executive team wanted a use-case shortlist.", "",
     None, "sp-silva", -70, -21),
    ("stlaurent", None, "Laptop deployment wave 1", "Bombardier Supplier Park", "Manufacturing", "lifecycle",
     "life-deploy", "Won", 31000, "confirmed", "decision_maker", "high", "under_3_months", "", "", None,
     "sp-kowalski", -90, -44),
    ("clearpath", None, "Copilot adoption pilot", "Yorkville Advisory", "Finance", "ai", "ai-copilot", "Won", 28000,
     "confirmed", "decision_maker", "high", "3_6_months", "", "", None, "sp-silva", -85, -15),
    ("granite", None, "Managed detection onboarding", "Seawall Properties", "Real estate", "security", "sec-mdr",
     "Won", 42000, "confirmed", "decision_maker", "high", "under_3_months", "", "", None, "sp-okafor", -100, -60),
    ("prairie", None, "Cloud readiness assessment", "Saskatoon Parts Depot", "Distribution", "cloud",
     "cloud-readiness", "Lost", 16000, "unknown", "influencer", "low", "6_plus_months", "", "", None, "sp-leblanc",
     -75, -33),
    ("maple", None, "SD-WAN deployment", "Ottawa Arts Collective", "Non-profit", "network", "net-sdwan", "Lost",
     48000, "indicated", "influencer", "medium", "6_plus_months", "", "", None, "sp-haddad", -120, -41),
    ("summit", None, "Device imaging", "Bow River Dental", "Healthcare", "lifecycle", "life-deploy", "Lost", 9000,
     "unknown", "unknown", "low", "unknown", "", "", None, None, -60, -25),
    ("pacifica", None, "Veeam backup hardening", "Island Tours Ltd.", "Tourism", "security", "sec-ransomware",
     "Won", 14000, "confirmed", "decision_maker", "high", "under_3_months", "", "", None, "sp-rao", -65, -12),
]
# fmt: on

CLOSE_REASONS = {
    "Lost": [
        "Customer chose to delay to next fiscal year",
        "Went with the incumbent provider",
        "No budget after re-forecast",
    ],
    "Won": [
        "Scope accepted after specialist call",
        "Partner resold as part of renewal",
        "Customer approved assessment ahead of audit",
    ],
}

TOUCH_TEMPLATES = {
    "call": [
        ("Discovery call with {contact}: walked through {customer}'s situation.", "connected"),
        ("Called {contact}; left voicemail about {topic}.", "voicemail"),
        ("Check-in call with {contact} on {topic}; next step agreed.", "connected"),
    ],
    "email": [
        ("Sent {contact} a short recap and the {service} overview.", "sent"),
        ("{contact} replied with questions about scope and timing.", "replied"),
        ("Followed up on {topic} with suggested times.", "sent"),
    ],
    "meeting": [("Joint meeting with {contact} and {customer} stakeholders.", "held")],
    "note": [("Internal note: {customer} wants to understand costs before involving procurement.", "")],
}


def _ws2016_deadline(today: date) -> date:
    real = date(2027, 1, 12)
    return real if (real - today).days >= 30 else today + timedelta(days=105)


def seed(session: Session, today: date | None = None) -> None:
    """Wipe and repopulate the database with the fictional scenario."""
    today = today or clock.today()
    rng = random.Random(468)
    engine = session.get_bind()
    Base.metadata.create_all(engine)
    for model in (Draft, Activity, Opportunity, Signal, Specialist, Partner):
        session.execute(delete(model))

    def on(offset: int) -> date:
        return today + timedelta(days=offset)

    def at(offset: int, hour: int) -> datetime:
        return datetime.combine(on(offset), time(hour, rng.choice((0, 15, 30, 45))))

    session.add_all(Specialist(id=i, name=n, title=t, practice=p, capacity=c) for i, n, t, p, c in SPECIALISTS)
    for (
        pid,
        name,
        ptype,
        tier,
        city,
        prov,
        verticals,
        vendors,
        contact,
        title,
        revenue,
        services,
        mix,
        used,
        about,
    ) in PARTNERS:
        first, last = contact.lower().replace("'", "").split(" ", 1)
        session.add(
            Partner(
                id=pid,
                name=name,
                partner_type=ptype,
                tier=tier,
                city=city,
                province=prov,
                verticals=verticals,
                vendors=vendors,
                contact_name=contact,
                contact_title=title,
                contact_email=f"{first[0]}.{last.replace(' ', '')}@{pid}.example",
                trailing_revenue=revenue,
                services_revenue=services,
                product_mix=mix,
                services_used=used,
                about=about,
            )
        )
    session.flush()

    signals: list[Signal] = []
    for pid, kind, source, practice, service, title, detail, strength, found, deadline in SIGNALS:
        due = _ws2016_deadline(today) if deadline == "ws2016" else (on(int(deadline)) if deadline else None)  # type: ignore[call-overload]
        signal = Signal(
            partner_id=pid,
            kind=kind,
            source=source,
            practice=practice,
            service_key=service,
            title=title,
            detail=detail,
            strength=strength,
            detected_on=on(found),
            deadline=due,
        )
        session.add(signal)
        signals.append(signal)
    session.flush()

    partners = {p.id: p for p in session.query(Partner)}
    for row in OPPORTUNITIES:
        (
            pid,
            sig,
            title,
            customer,
            industry,
            practice,
            service,
            stage,
            value,
            budget,
            authority,
            need,
            timeline,
            challenge,
            next_step,
            due_offset,
            specialist,
            created,
            changed,
        ) = row
        closed = stage in ("Won", "Lost")
        origin = signals[sig] if sig is not None else None
        if origin is not None:
            origin.status = "actioned"
        opp = Opportunity(
            partner_id=pid,
            signal_id=origin.id if origin else None,
            title=title,
            end_customer=customer,
            industry=industry,
            practice=practice,
            service_key=service,
            stage=stage,
            value=value,
            budget=budget,
            authority=authority,
            need=need,
            timeline=timeline,
            challenge=challenge,
            next_step=next_step,
            next_step_due=None if due_offset is None else on(due_offset),
            specialist_id=specialist,
            created_on=on(created),
            stage_changed_on=on(changed),
            closed_on=on(changed) if closed else None,
            close_reason=rng.choice(CLOSE_REASONS[stage]) if closed else "",
        )
        session.add(opp)
        session.flush()
        _seed_touches(session, rng, opp, partners[pid], created, changed, closed, at)
    # A realistic week of prospecting touches that are not tied to an opportunity yet.
    for day in range(-55, 1):
        if on(day).weekday() >= 5:
            continue
        for _ in range(rng.randint(1, 3)):
            partner = rng.choice(list(partners.values()))
            kind = rng.choice(("call", "email", "email"))
            text, outcome = rng.choice(TOUCH_TEMPLATES[kind])
            session.add(
                Activity(
                    partner_id=partner.id,
                    kind=kind,
                    outcome=outcome,
                    occurred_at=at(day, rng.randint(9, 16)),
                    summary=text.format(
                        contact=partner.contact_name.split()[0],
                        customer="a customer",
                        topic="services attach on recent orders",
                        service="services catalog",
                    ),
                )
            )
    session.commit()


def _seed_touches(session, rng, opp, partner, created, changed, closed, at) -> None:
    service = SERVICES_BY_KEY[opp.service_key].name
    first = partner.contact_name.split()[0]
    end = changed if closed else -rng.randint(0, 9)
    span = max(end - created, 1)
    count = 2 + min(4, span // 7)
    offsets = sorted({created + round(span * i / count) for i in range(count)} | {end})
    for index, offset in enumerate(offsets):
        kind = "call" if index == 0 else rng.choice(("call", "email", "email", "meeting", "note"))
        text, outcome = rng.choice(TOUCH_TEMPLATES[kind])
        session.add(
            Activity(
                partner_id=partner.id,
                opportunity_id=opp.id,
                kind=kind,
                outcome=outcome,
                occurred_at=at(min(offset, 0), rng.randint(9, 16)),
                summary=text.format(contact=first, customer=opp.end_customer, topic=inline(service), service=service),
            )
        )
    if opp.specialist_id:
        session.add(
            Activity(
                partner_id=partner.id,
                opportunity_id=opp.id,
                kind="handoff",
                outcome="accepted",
                occurred_at=at(min(changed, 0), 11),
                summary=f"Handoff brief sent to {SPECIALIST_NAMES[opp.specialist_id]}; specialist accepted.",
            )
        )
    if closed:
        session.add(
            Activity(
                partner_id=partner.id,
                opportunity_id=opp.id,
                kind="stage",
                outcome=opp.stage.lower(),
                occurred_at=at(changed, 15),
                summary=f"Marked {opp.stage}: {opp.close_reason}.",
            )
        )
