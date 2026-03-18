"""
Marketing Agent — Analyze, Recommend, Implement.

Approval policy: controlled by marketing_data.AUTO_APPROVE_MARKETING_ACTIONS
  True  → recommendations run immediately in mock/dev mode (no manual gate)
  False → status set to 'pending_approval' and waits for human trigger

Replace mock analysis methods with live API calls (SEMrush, Google Ads API,
Meta Marketing API) as integrations become available.
"""

import json
import logging
from datetime import datetime, timezone

try:
    import agent_registry as _registry
except Exception:
    _registry = None

import marketing_data as _md

logger = logging.getLogger("marketing_agent")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return datetime.now(timezone.utc).isoformat()

def _set(status, task=None):
    if _registry:
        try:
            _registry.set_status("MarketingAgent", status, task)
        except Exception:
            pass

def _log(group_id, action, result, status="completed"):
    entry = {
        "timestamp": _now(),
        "group_id": group_id,
        "action": action,
        "status": status,
        "result_summary": str(result)[:200],
    }
    logger.info(json.dumps(entry))
    return entry

# ---------------------------------------------------------------------------
# MarketingAgent
# ---------------------------------------------------------------------------

class MarketingAgent:

    def __init__(self):
        if _registry:
            try:
                _registry.register(
                    "MarketingAgent",
                    "Marketing intelligence: SEO, Google Ads, Facebook Ads analysis + implementation"
                )
            except Exception:
                pass
        self.auto_approve = _md.AUTO_APPROVE_MARKETING_ACTIONS
        self._audit_log = []

    # ------------------------------------------------------------------
    # SEO
    # ------------------------------------------------------------------

    def run_seo_analysis(self, business_group_id):
        _set("busy", f"run_seo_analysis:{business_group_id}")
        try:
            seo = _md.get_seo(business_group_id)
            competitors = _md.get_competitors(business_group_id)
            if not seo:
                return {"error": f"Unknown group: {business_group_id}"}

            # Derive competitor keyword gap
            all_comp_kws = []
            for c in (competitors or []):
                for kw in c.get("seo", {}).get("top_keywords", []):
                    all_comp_kws.append({
                        "keyword": kw["kw"],
                        "competitor": c["name"],
                        "position": kw["position"],
                        "volume": kw["volume"],
                    })

            result = {
                "group_id": business_group_id,
                "analysis_type": "seo",
                "timestamp": _now(),
                "health_score": seo["health_score"],
                "organic_traffic": seo["organic_traffic"],
                "keywords_ranked": seo["keywords_ranked"],
                "top_opportunities": seo["keyword_opportunities"][:5],
                "critical_issues": [i for i in seo["technical_issues"] if i["severity"] == "high"],
                "competitor_keyword_gaps": all_comp_kws[:12],
                "ranking_distribution": seo["ranking_distribution"],
                "top_pages": seo["top_pages"],
                "recommendations_generated": len([
                    r for r in (_md.get_recommendations(business_group_id) or [])
                    if r["channel"] == "seo"
                ]),
            }
            _log(business_group_id, "run_seo_analysis", result)
            return result
        finally:
            _set("idle", f"run_seo_analysis:{business_group_id}")

    def generate_seo_optimization_plan(self, business_group_id):
        _set("busy", f"generate_seo_plan:{business_group_id}")
        try:
            recs = [r for r in (_md.get_recommendations(business_group_id) or []) if r["channel"] == "seo"]
            kg = _md.get_knowledge_graph(business_group_id)
            kg_insights = (kg or {}).get("insights", [])

            plan = {
                "group_id": business_group_id,
                "plan_type": "seo_optimization",
                "timestamp": _now(),
                "recommendations": recs,
                "knowledge_graph_insights": [i for i in kg_insights if i.get("type") in ("gap","performance")],
                "priority_order": sorted(recs, key=lambda r: r["priority"]),
                "auto_approve": self.auto_approve,
                "total_expected_leads": sum(
                    int(r["expected_leads_impact"].replace("+","").replace("/mo","").replace(" (seasonal)","").strip() or "0")
                    for r in recs if r.get("expected_leads_impact","").startswith("+")
                ),
            }

            # Auto-approve if policy allows
            if self.auto_approve:
                for rec in recs:
                    if rec.get("status") == "ready" and not rec.get("requires_approval", True):
                        _md.update_recommendation_status(business_group_id, rec["id"], "pending_approval")

            _log(business_group_id, "generate_seo_optimization_plan", f"{len(recs)} SEO recs generated")
            return plan
        finally:
            _set("idle", f"generate_seo_plan:{business_group_id}")

    def implement_seo_optimizations(self, business_group_id, rec_ids=None):
        _set("busy", f"implement_seo:{business_group_id}")
        try:
            recs = _md.get_recommendations(business_group_id) or []
            results = []
            for rec in recs:
                if rec["channel"] != "seo":
                    continue
                if rec_ids and rec["id"] not in rec_ids:
                    continue
                if not self.auto_approve and rec.get("requires_approval", False):
                    results.append({"id": rec["id"], "status": "pending_approval", "message": "Awaiting manual approval"})
                    continue
                # Simulate implementation
                _md.update_recommendation_status(business_group_id, rec["id"], "completed")
                results.append({
                    "id": rec["id"],
                    "title": rec["title"],
                    "status": "completed",
                    "simulated": True,
                    "timestamp": _now(),
                    "message": f"[MOCK] SEO optimization '{rec['title']}' executed successfully.",
                })
                _log(business_group_id, f"implement_seo:{rec['id']}", results[-1])
            return {"group_id": business_group_id, "channel": "seo", "results": results}
        finally:
            _set("idle", f"implement_seo:{business_group_id}")

    # ------------------------------------------------------------------
    # Google Ads
    # ------------------------------------------------------------------

    def run_google_ads_analysis(self, business_group_id):
        _set("busy", f"run_gads_analysis:{business_group_id}")
        try:
            gads = _md.get_google_ads(business_group_id)
            competitors = _md.get_competitors(business_group_id)
            if not gads:
                return {"error": f"Unknown group: {business_group_id}"}

            wasted = gads.get("wasted_spend", {})
            comp_ad_examples = []
            for c in (competitors or []):
                for ad in c.get("google_ads", {}).get("ad_examples", [])[:1]:
                    comp_ad_examples.append({"competitor": c["name"], "ad": ad})

            result = {
                "group_id": business_group_id,
                "analysis_type": "google_ads",
                "timestamp": _now(),
                "total_spend": gads["spend"],
                "total_conversions": gads["conversions"],
                "roas": gads.get("roas"),
                "cpa": gads["cpa"],
                "quality_score_avg": gads["quality_score_avg"],
                "wasted_spend_total": wasted.get("total", 0),
                "wasted_spend_items": wasted.get("items", []),
                "flagged_keywords": [k for k in gads["keywords"] if k.get("status") == "flagged"],
                "top_campaigns": sorted(gads["campaigns"], key=lambda c: c.get("roas") or 0, reverse=True)[:3],
                "competitor_ads": comp_ad_examples[:4],
                "search_term_insights": gads["search_terms"],
                "recommendations_generated": len([
                    r for r in (_md.get_recommendations(business_group_id) or [])
                    if r["channel"] == "google_ads"
                ]),
            }
            _log(business_group_id, "run_google_ads_analysis", result)
            return result
        finally:
            _set("idle", f"run_gads_analysis:{business_group_id}")

    def generate_google_ads_recommendations(self, business_group_id):
        _set("busy", f"generate_gads_recs:{business_group_id}")
        try:
            recs = [r for r in (_md.get_recommendations(business_group_id) or []) if r["channel"] == "google_ads"]
            if self.auto_approve:
                for rec in recs:
                    if rec.get("status") == "ready" and not rec.get("requires_approval", True):
                        _md.update_recommendation_status(business_group_id, rec["id"], "pending_approval")
            plan = {
                "group_id": business_group_id,
                "plan_type": "google_ads_recommendations",
                "timestamp": _now(),
                "recommendations": recs,
                "auto_approve": self.auto_approve,
            }
            _log(business_group_id, "generate_google_ads_recommendations", f"{len(recs)} recs")
            return plan
        finally:
            _set("idle", f"generate_gads_recs:{business_group_id}")

    def implement_google_ads_optimizations(self, business_group_id, rec_ids=None):
        _set("busy", f"implement_gads:{business_group_id}")
        try:
            recs = _md.get_recommendations(business_group_id) or []
            results = []
            for rec in recs:
                if rec["channel"] != "google_ads":
                    continue
                if rec_ids and rec["id"] not in rec_ids:
                    continue
                if not self.auto_approve and rec.get("requires_approval", False):
                    results.append({"id": rec["id"], "status": "pending_approval"})
                    continue
                _md.update_recommendation_status(business_group_id, rec["id"], "completed")
                results.append({
                    "id": rec["id"], "title": rec["title"], "status": "completed",
                    "simulated": True, "timestamp": _now(),
                    "message": f"[MOCK] Google Ads optimization '{rec['title']}' executed.",
                })
                _log(business_group_id, f"implement_gads:{rec['id']}", results[-1])
            return {"group_id": business_group_id, "channel": "google_ads", "results": results}
        finally:
            _set("idle", f"implement_gads:{business_group_id}")

    # ------------------------------------------------------------------
    # Facebook Ads
    # ------------------------------------------------------------------

    def run_facebook_ads_analysis(self, business_group_id):
        _set("busy", f"run_fb_analysis:{business_group_id}")
        try:
            fb = _md.get_facebook_ads(business_group_id)
            competitors = _md.get_competitors(business_group_id)
            if not fb:
                return {"error": f"Unknown group: {business_group_id}"}

            fatigued = [c for c in fb.get("creatives", []) if c.get("fatigue_score", 0) > 50]
            comp_ads = []
            for c in (competitors or []):
                for ad in c.get("facebook_ads", {}).get("ad_examples", [])[:1]:
                    comp_ads.append({"competitor": c["name"], "ad": ad})

            result = {
                "group_id": business_group_id,
                "analysis_type": "facebook_ads",
                "timestamp": _now(),
                "total_spend": fb["spend"],
                "total_leads": fb["leads"],
                "cpm": fb["cpm"],
                "cpa": fb["cpa"],
                "frequency": fb["frequency"],
                "fatigued_creatives": fatigued,
                "top_audiences": sorted(fb["audiences"], key=lambda a: a.get("performance_score", 0), reverse=True)[:3],
                "competitor_ads": comp_ads[:4],
                "funnel_breakdown": fb["funnel_breakdown"],
                "recommendations_generated": len([
                    r for r in (_md.get_recommendations(business_group_id) or [])
                    if r["channel"] == "facebook_ads"
                ]),
            }
            _log(business_group_id, "run_facebook_ads_analysis", result)
            return result
        finally:
            _set("idle", f"run_fb_analysis:{business_group_id}")

    def generate_facebook_ads_recommendations(self, business_group_id):
        _set("busy", f"generate_fb_recs:{business_group_id}")
        try:
            recs = [r for r in (_md.get_recommendations(business_group_id) or []) if r["channel"] == "facebook_ads"]
            if self.auto_approve:
                for rec in recs:
                    if rec.get("status") == "ready" and not rec.get("requires_approval", True):
                        _md.update_recommendation_status(business_group_id, rec["id"], "pending_approval")
            plan = {
                "group_id": business_group_id,
                "plan_type": "facebook_ads_recommendations",
                "timestamp": _now(),
                "recommendations": recs,
                "auto_approve": self.auto_approve,
            }
            _log(business_group_id, "generate_facebook_ads_recommendations", f"{len(recs)} recs")
            return plan
        finally:
            _set("idle", f"generate_fb_recs:{business_group_id}")

    def implement_facebook_ads_optimizations(self, business_group_id, rec_ids=None):
        _set("busy", f"implement_fb:{business_group_id}")
        try:
            recs = _md.get_recommendations(business_group_id) or []
            results = []
            for rec in recs:
                if rec["channel"] != "facebook_ads":
                    continue
                if rec_ids and rec["id"] not in rec_ids:
                    continue
                if not self.auto_approve and rec.get("requires_approval", False):
                    results.append({"id": rec["id"], "status": "pending_approval"})
                    continue
                _md.update_recommendation_status(business_group_id, rec["id"], "completed")
                results.append({
                    "id": rec["id"], "title": rec["title"], "status": "completed",
                    "simulated": True, "timestamp": _now(),
                    "message": f"[MOCK] Facebook Ads optimization '{rec['title']}' executed.",
                })
                _log(business_group_id, f"implement_fb:{rec['id']}", results[-1])
            return {"group_id": business_group_id, "channel": "facebook_ads", "results": results}
        finally:
            _set("idle", f"implement_fb:{business_group_id}")

    # ------------------------------------------------------------------
    # Knowledge Graph / Intelligence
    # ------------------------------------------------------------------

    def build_marketing_intelligence_graph(self, business_group_id):
        _set("busy", f"build_kg:{business_group_id}")
        try:
            kg = _md.get_knowledge_graph(business_group_id)
            competitors = _md.get_competitors(business_group_id) or []
            if not kg:
                return {"error": f"Unknown group: {business_group_id}"}

            entities = kg["entities"]
            entity_count = sum(len(v) for v in entities.values())
            relationship_count = len(kg["relationships"])

            result = {
                "group_id": business_group_id,
                "timestamp": _now(),
                "entity_count": entity_count,
                "relationship_count": relationship_count,
                "entities": entities,
                "relationships": kg["relationships"],
                "insights": kg["insights"],
                "competitor_count": len(competitors),
                "high_confidence_insights": [i for i in kg["insights"] if i.get("confidence", 0) >= 85],
            }
            _log(business_group_id, "build_marketing_intelligence_graph", f"{entity_count} entities, {relationship_count} relationships")
            return result
        finally:
            _set("idle", f"build_kg:{business_group_id}")

    def refresh_competitor_intelligence(self, business_group_id):
        _set("busy", f"refresh_competitors:{business_group_id}")
        try:
            competitors = _md.get_competitors(business_group_id) or []
            result = {
                "group_id": business_group_id,
                "timestamp": _now(),
                "competitors_analyzed": len(competitors),
                "competitors": [
                    {
                        "name": c["name"],
                        "domain": c["domain"],
                        "visibility_score": c["visibility_score"],
                        "strengths": c["strengths"],
                        "weaknesses": c["weaknesses"],
                        "opportunity_gaps": c["opportunity_gaps"],
                        "seo_keywords_count": c.get("seo", {}).get("keywords_ranking", 0),
                        "estimated_ad_spend": c.get("google_ads", {}).get("estimated_spend", 0),
                    }
                    for c in competitors
                ],
                "simulated": True,
                "note": "Replace with live SEMrush/Ahrefs/SpyFu API calls for production.",
            }
            _log(business_group_id, "refresh_competitor_intelligence", f"{len(competitors)} competitors")
            return result
        finally:
            _set("idle", f"refresh_competitors:{business_group_id}")

    def generate_cross_channel_insights(self, business_group_id):
        _set("busy", f"cross_channel_insights:{business_group_id}")
        try:
            kg = _md.get_knowledge_graph(business_group_id) or {}
            recs = _md.get_recommendations(business_group_id) or []

            cross_channel_recs = [r for r in recs if r["channel"] == "cross_channel"]
            all_insights = kg.get("insights", [])

            result = {
                "group_id": business_group_id,
                "timestamp": _now(),
                "cross_channel_recommendations": cross_channel_recs,
                "knowledge_graph_insights": all_insights,
                "high_priority_actions": [
                    r for r in recs if r["priority"] == 1
                ],
                "channel_performance_summary": {
                    "seo": _md.get_seo(business_group_id),
                    "google_ads_cpa": (_md.get_google_ads(business_group_id) or {}).get("cpa"),
                    "facebook_cpa": (_md.get_facebook_ads(business_group_id) or {}).get("cpa"),
                },
            }
            _log(business_group_id, "generate_cross_channel_insights", f"{len(all_insights)} insights")
            return result
        finally:
            _set("idle", f"cross_channel_insights:{business_group_id}")

    # ------------------------------------------------------------------
    # Queue / Approval
    # ------------------------------------------------------------------

    def get_implementation_queue(self, business_group_id):
        recs = _md.get_recommendations(business_group_id) or []
        return {
            "group_id": business_group_id,
            "timestamp": _now(),
            "queue": [
                r for r in recs if r.get("status") in ("ready", "pending_approval", "running")
            ],
            "auto_approve_enabled": self.auto_approve,
        }

    def approve_recommendation(self, business_group_id, rec_id):
        _set("busy", f"approve:{rec_id}")
        try:
            recs = _md.get_recommendations(business_group_id) or []
            for rec in recs:
                if rec["id"] == rec_id:
                    _md.update_recommendation_status(business_group_id, rec_id, "running")
                    # Simulate execution
                    _md.update_recommendation_status(business_group_id, rec_id, "completed")
                    result = {
                        "id": rec_id, "title": rec["title"],
                        "status": "completed", "simulated": True, "timestamp": _now(),
                    }
                    _log(business_group_id, f"approve:{rec_id}", result)
                    return result
            return {"error": f"Recommendation {rec_id} not found"}
        finally:
            _set("idle", f"approve:{rec_id}")

    def run_full_analysis(self, business_group_id):
        """Run all analyses for a group in sequence. Suitable for unattended execution."""
        _set("busy", f"full_analysis:{business_group_id}")
        results = {}
        try:
            results["seo"] = self.run_seo_analysis(business_group_id)
            results["google_ads"] = self.run_google_ads_analysis(business_group_id)
            results["facebook_ads"] = self.run_facebook_ads_analysis(business_group_id)
            results["knowledge_graph"] = self.build_marketing_intelligence_graph(business_group_id)
            results["competitors"] = self.refresh_competitor_intelligence(business_group_id)
            results["cross_channel"] = self.generate_cross_channel_insights(business_group_id)
            _log(business_group_id, "run_full_analysis", "All channels analyzed")
            return {"group_id": business_group_id, "timestamp": _now(), "results": results}
        finally:
            _set("idle", f"full_analysis:{business_group_id}")

    def get_status_summary(self):
        summary = {}
        for gid in _md.BUSINESS_GROUPS:
            recs = _md.get_recommendations(gid) or []
            summary[gid] = {
                "name": _md.BUSINESS_GROUPS[gid]["name"],
                "total_recommendations": len(recs),
                "ready": len([r for r in recs if r["status"] == "ready"]),
                "completed": len([r for r in recs if r["status"] == "completed"]),
                "draft": len([r for r in recs if r["status"] == "draft"]),
                "pending": len([r for r in recs if r["status"] == "pending_approval"]),
            }
        return {"timestamp": _now(), "auto_approve": self.auto_approve, "groups": summary}
