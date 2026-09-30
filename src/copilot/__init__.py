"""The operations copilot: joins the plant and the supply network, analyses the impact of predicted failures, and plans actions.

It builds on pdm_oee (sense) and supply_ontology (governed supply data) and never the other way round.
Layers import downward only: api and ui, then services, then data_pipeline, then core.
"""
