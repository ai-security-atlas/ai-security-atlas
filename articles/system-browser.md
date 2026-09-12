Browser and computer-use integrations extend a [tool-using agent](../nodes/system-agent.md) so it can drive a real browser or desktop: navigating pages, reading documents, clicking, and typing. Rendered page content and document text become model observations, and the model's decisions become actions on the host or the web.

## Trust boundary

This component pulls arbitrary third-party content directly into the agent's decision loop. A web page or document is untrusted input, yet here it both informs the model and can trigger consequential actions, so the line between "content to read" and "instructions to follow" is thin. Because pages can carry text inside images, screenshots, or other media, the component is relevant to instructions carried through multimodal content, where directives hidden in rendered material may be interpreted as commands rather than data.

For documented cases of untrusted page and document content influencing integrated applications, see the cited sources.
