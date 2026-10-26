# My agent: SiteSafeAgent
One-liner: A conversational agent that helps construction and industrial safety managers inspect safety hazards from photos and live camera feeds with a catalog of OSHA 1926 standards, corrective action plans, and printable PDF inspection reports.

Tool coverage:
- Memory: Remembers safety inspector profile, active jobsite ID, recent violation history, and inspection audit notes across sessions.
- Tools: Hazard analyzer (photo and live video detection), OSHA 1926 regulation lookup, risk index calculator, and PDF safety audit report generator.
- Catalog/UI: Catalog of OSHA 1926 construction safety standards and site hazard logs rendered as rich A2UI cards and tables.
- Image gen: Generates hazard corrective action diagrams / safety warning visuals using gemini-3.1-flash-lite-image.
- Sandbox: Computes site risk scores, statistical severity weighting, and estimated OSHA penalty ranges.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch: code sandbox for risk calculations, live multimodal camera feed, live external API (weather conditions for site safety).
