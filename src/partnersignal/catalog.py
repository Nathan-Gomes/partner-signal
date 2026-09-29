"""The professional-services catalog: practices, services, stages and the qualification playbook.

Everything here is fictional reference data shaped like a distributor's services
portfolio. Keeping it in one module means the scoring rules, the AI prompts and the
UI all read the same definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PRACTICES: dict[str, str] = {
    "security": "Cybersecurity",
    "cloud": "Cloud & hybrid IT",
    "network": "Networking",
    "ai": "AI & data",
    "lifecycle": "Lifecycle & deployment",
    "training": "Training & enablement",
}


@dataclass(frozen=True)
class Service:
    key: str
    practice: str
    name: str
    kind: str  # assessment | project | managed | training
    typical_value: int  # CAD, used only as a default estimate
    duration: str
    summary: str


SERVICES: list[Service] = [
    Service(
        "sec-posture",
        "security",
        "Security posture assessment",
        "assessment",
        18000,
        "3 weeks",
        "Baseline controls review against CIS v8 with a prioritized remediation roadmap.",
    ),
    Service(
        "sec-ransomware",
        "security",
        "Ransomware readiness review",
        "assessment",
        14000,
        "2 weeks",
        "Backup, recovery and incident-response tabletop for a named customer environment.",
    ),
    Service(
        "sec-mdr",
        "security",
        "Managed detection onboarding",
        "managed",
        42000,
        "6 weeks",
        "Endpoint and identity telemetry onboarding into a 24x7 managed detection service.",
    ),
    Service(
        "cloud-readiness",
        "cloud",
        "Cloud readiness assessment",
        "assessment",
        16000,
        "3 weeks",
        "Workload inventory, dependency mapping and a landing-zone recommendation.",
    ),
    Service(
        "cloud-migration",
        "cloud",
        "Server workload migration",
        "project",
        65000,
        "8-12 weeks",
        "Lift-and-optimize migration of on-premises servers to Azure or AWS.",
    ),
    Service(
        "cloud-vmware",
        "cloud",
        "Virtualization exit planning",
        "assessment",
        22000,
        "4 weeks",
        "Licensing impact model and platform options for customers re-evaluating VMware.",
    ),
    Service(
        "net-assessment",
        "network",
        "Network health assessment",
        "assessment",
        12000,
        "2 weeks",
        "Switching, wireless and WAN capacity review with a refresh bill of materials.",
    ),
    Service(
        "net-sdwan",
        "network",
        "SD-WAN deployment",
        "project",
        48000,
        "6-10 weeks",
        "Design and staged rollout of SD-WAN across branch sites.",
    ),
    Service(
        "net-segmentation",
        "network",
        "Segmentation & zero-trust design",
        "project",
        36000,
        "5 weeks",
        "Network segmentation plan for remote access, OT or regulated workloads.",
    ),
    Service(
        "ai-readiness",
        "ai",
        "AI readiness workshop",
        "assessment",
        9500,
        "1 week",
        "Use-case prioritization, data-readiness check and governance guardrails.",
    ),
    Service(
        "ai-copilot",
        "ai",
        "Copilot adoption pilot",
        "project",
        28000,
        "6 weeks",
        "Permissions clean-up, pilot group enablement and adoption measurement.",
    ),
    Service(
        "ai-governance",
        "ai",
        "Data governance assessment",
        "assessment",
        17000,
        "3 weeks",
        "Sensitive-data discovery and labelling policy before AI tools are enabled.",
    ),
    Service(
        "life-deploy",
        "lifecycle",
        "Device deployment & imaging",
        "project",
        31000,
        "4-8 weeks",
        "Staging, imaging, asset tagging and white-glove delivery for device refreshes.",
    ),
    Service(
        "life-itad",
        "lifecycle",
        "IT asset disposition",
        "project",
        11000,
        "2-4 weeks",
        "Certified data destruction and remarketing for retired hardware.",
    ),
    Service(
        "life-eos",
        "lifecycle",
        "End-of-support migration",
        "project",
        39000,
        "6-10 weeks",
        "Plan and execute moves off operating systems and hardware reaching end of support.",
    ),
    Service(
        "train-cert",
        "training",
        "Technical certification bootcamp",
        "training",
        8500,
        "1-2 weeks",
        "Instructor-led vendor certification path for a partner's engineers.",
    ),
    Service(
        "train-sales",
        "training",
        "Services sales enablement",
        "training",
        6000,
        "2 days",
        "Discovery-conversation training for a partner's account managers.",
    ),
]
SERVICES_BY_KEY = {service.key: service for service in SERVICES}

# Stage order, default win probability, and the follow-up cadence (days) that applies
# after a touch in that stage.
STAGES: list[tuple[str, float, int]] = [
    ("Prospect", 0.05, 4),
    ("Discovery", 0.15, 3),
    ("Qualified", 0.35, 5),
    ("Solutioning", 0.55, 4),
    ("Proposal", 0.75, 2),
    ("Won", 1.0, 30),
    ("Lost", 0.0, 90),
]
STAGE_NAMES = [name for name, _, _ in STAGES]
OPEN_STAGES = STAGE_NAMES[:5]
STAGE_PROBABILITY = {name: probability for name, probability, _ in STAGES}
STAGE_CADENCE = {name: cadence for name, _, cadence in STAGES}

BANT_LEVELS: dict[str, list[str]] = {
    "budget": ["unknown", "indicated", "confirmed"],
    "authority": ["unknown", "influencer", "decision_maker"],
    "need": ["unknown", "low", "medium", "high"],
    "timeline": ["unknown", "6_plus_months", "3_6_months", "under_3_months"],
}


@dataclass(frozen=True)
class Playbook:
    practice: str
    triggers: list[str]
    questions: list[str]
    ai_use_cases: list[str] = field(default_factory=list)
    keywords: dict[str, int] = field(default_factory=dict)


PLAYBOOKS: dict[str, Playbook] = {
    "security": Playbook(
        "security",
        triggers=[
            "Cyber-insurance renewal questionnaire",
            "Recent incident or phishing event",
            "Audit or regulatory finding",
            "Firewall or endpoint purchase without services",
        ],
        questions=[
            "When was the last time backups were restored in a test?",
            "What does the cyber-insurance renewal require this year?",
            "Who would lead the response if ransomware hit tomorrow?",
            "Which compliance frameworks does the customer report against?",
        ],
        ai_use_cases=[
            "Security alert triage summaries for small SOC teams",
            "Phishing simulation content tailored by department",
        ],
        keywords={
            "ransomware": 5,
            "breach": 5,
            "phishing": 4,
            "insurance": 4,
            "insurer": 4,
            "restore": 3,
            "mfa": 3,
            "audit": 3,
            "compliance": 3,
            "firewall": 3,
            "endpoint": 3,
            "security": 3,
            "backup": 2,
            "soc 2": 4,
            "pipeda": 3,
            "incident": 3,
            "vulnerab": 3,
        },
    ),
    "cloud": Playbook(
        "cloud",
        triggers=[
            "Datacenter lease or colocation contract ending",
            "Hardware refresh due",
            "Virtualization licensing change",
            "Microsoft 365 / Azure consumption growth",
        ],
        questions=[
            "Which workloads are still on-premises, and what do they depend on?",
            "Is there a hardware refresh or lease date forcing the decision?",
            "How is the customer affected by virtualization licensing changes?",
            "Who owns the cloud budget: IT or the business unit?",
        ],
        ai_use_cases=[
            "Workload discovery summaries from inventory exports",
            "Cost-optimization recommendations from consumption data",
        ],
        keywords={
            "migrat": 4,
            "azure": 4,
            "aws": 4,
            "cloud": 3,
            "on-prem": 4,
            "vmware": 5,
            "datacenter": 4,
            "data center": 4,
            "server": 2,
            "hybrid": 3,
            "lease": 3,
            "colocation": 3,
            "broadcom": 4,
            "virtual": 2,
        },
    ),
    "network": Playbook(
        "network",
        triggers=[
            "New site or office move",
            "Wi-Fi complaints or coverage gaps",
            "Switching reaching end of life",
            "Remote-access or OT segmentation needs",
        ],
        questions=[
            "How many sites are in scope, and are any opening or moving?",
            "Where do users feel the network is slowest today?",
            "Is any switching or wireless hardware past end of sale?",
            "Are there operational-technology devices on the same network as users?",
        ],
        ai_use_cases=[
            "Network telemetry anomaly summaries",
            "Helpdesk ticket clustering to find recurring connectivity issues",
        ],
        keywords={
            "wi-fi": 4,
            "wifi": 4,
            "wireless": 4,
            "network": 3,
            "switch": 3,
            "sd-wan": 5,
            "wan": 3,
            "site": 2,
            "warehouse": 2,
            "connectivity": 4,
            "segment": 4,
            "latency": 3,
            "remote access": 3,
            "vpn": 3,
            "branch": 3,
        },
    ),
    "ai": Playbook(
        "ai",
        triggers=[
            "Copilot or AI licence purchases",
            "Leadership asking for an AI plan",
            "Sensitive data concerns blocking AI",
            "Manual document-heavy processes",
        ],
        questions=[
            "Which repetitive tasks would the customer most like to remove?",
            "Where does sensitive data live, and is it labelled?",
            "Has leadership set any rules for using AI tools?",
            "How would the customer measure a successful pilot in 60 days?",
        ],
        ai_use_cases=[
            "Contract and invoice document extraction",
            "Internal knowledge assistant over policies and SOPs",
            "Meeting summaries and action tracking for field teams",
        ],
        keywords={
            "ai": 3,
            "copilot": 5,
            "machine learning": 4,
            "genai": 5,
            "chatbot": 4,
            "automation": 3,
            "automate": 3,
            "llm": 5,
            "use case": 3,
            "governance": 3,
            "sensitive data": 4,
            "analytics": 2,
            "data quality": 3,
        },
    ),
    "lifecycle": Playbook(
        "lifecycle",
        triggers=[
            "Operating system or server end of support",
            "Large device refresh order",
            "Office consolidation leaving surplus hardware",
            "Leasing return deadlines",
        ],
        questions=[
            "How many devices are in the refresh, and across how many locations?",
            "Who images and ships devices today, and how long does it take?",
            "What happens to retired hardware and the data on it?",
            "Are any servers still running an operating system near end of support?",
        ],
        ai_use_cases=["Asset-inventory reconciliation between purchase and deployment records"],
        keywords={
            "refresh": 4,
            "laptop": 3,
            "device": 3,
            "imaging": 4,
            "end of support": 5,
            "end-of-support": 5,
            "eol": 4,
            "windows server 2016": 5,
            "rollout": 3,
            "deploy": 2,
            "disposal": 4,
            "retire": 3,
            "asset": 2,
            "itad": 5,
        },
    ),
    "training": Playbook(
        "training",
        triggers=[
            "Partner hiring engineers",
            "New vendor authorization requirement",
            "Low services attach on product deals",
            "Certification renewal deadlines",
        ],
        questions=[
            "Which certifications does the partner need for its next vendor tier?",
            "How many engineers or sellers would attend?",
            "Where do the partner's account managers lose confidence in discovery?",
            "Does the partner prefer live, virtual or self-paced delivery?",
        ],
        ai_use_cases=["AI-assisted discovery call coaching for account managers"],
        keywords={
            "training": 4,
            "certif": 5,
            "skills": 3,
            "skill gap": 5,
            "enablement": 4,
            "onboard": 2,
            "bootcamp": 4,
            "course": 3,
            "learn": 2,
            "new hire": 3,
        },
    ),
}

BANT_QUESTIONS: dict[str, str] = {
    "budget": "Is there budget set aside for this, or would it need to be requested?",
    "authority": "Who else needs to be involved to approve a project like this?",
    "need": "What happens if this problem is still unsolved in six months?",
    "timeline": "Is there a date driving this: a renewal, audit, lease or fiscal year-end?",
}
