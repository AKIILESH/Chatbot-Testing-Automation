import json
from pathlib import Path
from typing import Dict, Any, List, Optional


def format_inr(number: int | float) -> str:
    """Formats an integer or float into Indian numbering format (lakhs/crores)."""
    s = str(int(number))
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


class ProcurementDataStore:
    """
    Central repository access for enterprise procurement datasets, purchase orders,
    requisitions, vendor directory, quotations, budgets, and compliance policies.
    """

    def __init__(self, data_file: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.data_file = Path(data_file or (base_dir / "data" / "procurement.json"))
        self._load()

    def _load(self):
        if not self.data_file.exists():
            raise FileNotFoundError(f"Procurement dataset missing at: {self.data_file}")
        with open(self.data_file, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    @property
    def purchase_requisitions(self) -> List[Dict[str, Any]]:
        return self._data.get("purchase_requisitions", [])

    @property
    def purchase_orders(self) -> List[Dict[str, Any]]:
        return self._data.get("purchase_orders", [])

    @property
    def vendors(self) -> List[Dict[str, Any]]:
        return self._data.get("vendors", [])

    @property
    def quotations(self) -> List[Dict[str, Any]]:
        return self._data.get("quotations", [])

    @property
    def budgets(self) -> Dict[str, Any]:
        return self._data.get("budgets", {})

    @property
    def policies(self) -> List[Dict[str, Any]]:
        return self._data.get("policies", [])

    @property
    def test_cases(self) -> List[Dict[str, Any]]:
        return self._data.get("test_cases", [])

    def get_pr(self, pr_id: str) -> Optional[Dict[str, Any]]:
        for pr in self.purchase_requisitions:
            if pr.get("id", "").upper() == pr_id.upper():
                return pr
        return None

    def get_po(self, po_id: str) -> Optional[Dict[str, Any]]:
        for po in self.purchase_orders:
            if po.get("id", "").upper() == po_id.upper():
                return po
        return None

    def get_vendor(self, query: str) -> Optional[Dict[str, Any]]:
        q = query.lower()
        for v in self.vendors:
            if v.get("id", "").lower() == q or q in v.get("name", "").lower():
                return v
        return None

    def get_budget(self, department: str) -> Optional[Dict[str, Any]]:
        for dept, vals in self.budgets.items():
            if dept.lower() == department.lower():
                return vals
        return None

    def build_context_string(self) -> str:
        """
        Builds a comprehensive, grounded context summary for LLM prompt augmentation.
        """
        pr_lines = [
            f"- {pr['id']}: Requester={pr['requester']}, Item={pr['item']}, Status='{pr['status']}', Cost=₹{format_inr(pr['estimated_cost'])}"
            for pr in self.purchase_requisitions
        ]
        po_lines = [
            f"- {po['id']}: Vendor='{po['vendor_name']}', Amount=₹{format_inr(po['amount'])}, Status='{po['status']}', Items='{po['items']}'"
            for po in self.purchase_orders
        ]
        vendor_lines = [
            f"- {v['id']}: {v['name']} ({v['category']}), Terms={v['payment_terms']}, Rating={v['rating']}"
            for v in self.vendors
        ]
        budget_lines = [
            f"- {dept}: Allocated=₹{format_inr(b['allocated'])}, Spent=₹{format_inr(b['spent'])}, Remaining=₹{format_inr(b['remaining'])}"
            for dept, b in self.budgets.items()
        ]
        policy_lines = [f"- {p['id']}: {p['rule']}" for p in self.policies]

        return (
            "ENTERPRISE PROCUREMENT DATABASE:\n\n"
            "Purchase Requisitions:\n" + "\n".join(pr_lines) + "\n\n"
            "Purchase Orders:\n" + "\n".join(po_lines) + "\n\n"
            "Approved Vendors:\n" + "\n".join(vendor_lines) + "\n\n"
            "Department Budgets:\n" + "\n".join(budget_lines) + "\n\n"
            "Corporate Procurement Policies:\n" + "\n".join(policy_lines)
        )


procurement_store = ProcurementDataStore()
