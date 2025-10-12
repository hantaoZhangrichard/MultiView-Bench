"""
Store all prompt templates for VLM and LLM interactions.
"""

VLM_SYSTEM_PROMPT = '''
You are a precise vision judge. The image shows colored world axes:

COORDINATE SYSTEM:
- X-axis: RED rod, pointing to positive X direction
- Y-axis: GREEN rod, pointing to positive Y direction
- Z-axis: BLUE rod, pointing to position Z direction
- Origin (0,0,0): YELLOW sphere, located at the center of the {central_object}
- Both CENTRAL and TARGET objects have the same scale in X, Y, Z dimensions

TASK:
Determine the relative position of the {target_object} compared to the {central_object} in terms of their geometric centers.

INSTRUCTIONS:
1. Only focus on axis {axis} for this view and only give answer for these axes.
2. Compare the TARGET center to the CENTRAL center along each of {axis}:
     • "+" if TARGET lies in the positive direction  
     • "–" if in the negative direction  
     • "0" if approximately equal (centers aligned along that axis)
3. Wrap your full step‑by‑step reasoning in `<think>…</think>`.  
4. Then emit exactly one line, wrapped in `<answer>…</answer>`, listing only axes {axis} with their sign or 0.  
Do **not** include any extra text or prose.
'''

VLM_USER_PROMPT = '''
CENTRAL: {central}
TARGET:  {target}

Return exactly:
<think>…step-by-step reasoning…</think>
<answer>(±X, ±Y, ±Z)</answer>

Valid examples:
  <think>I see red and green axes…</think>
  <answer>(+X, -Y)</answer>

  <think>Blue axis only is clear…</think>
  <answer>(-Z)</answer>
'''


# LLM planner/aggregator prompts
LLM_SYSTEM_PROMPT = '''
You control a camera in a 3D scene. Your goal is to decide the signs (+,0,−) 
of TARGET relative to CENTRAL on axes X,Y,Z by choosing successive viewpoints.

**Camera Coordinate System:**
- Azimuth 0°: X-axis points towards viewer, Y-axis points right
- As azimuth increases (clockwise rotation):
  - Azimuth 90°: Y-axis points towards viewer, X-axis points left
  - Azimuth 180°: X-axis points away from viewer, Y-axis points left  
  - Azimuth 270°: Y-axis points away from viewer, X-axis points right
- Elevation 0°: Camera views from directly above (top-down)
- Elevation 90°: Camera views from horizontal level
- Elevation 180°: Camera views from directly below (bottom-up)

On every turn you will receive:
- threshold τ (a float in [0,1])
- belief_state: 
    { 
      "X": {"+" : p_plus, "0": p_zero, "-" : p_minus}, 
      "Y": {...}, 
      "Z": {...} 
    }
- history: a list of previously checked views, each entry: 
    {
      "view":   {"az": az_deg, "el": el_deg},
      "answer": "(±X, ±Y, ±Z)" or shorter,
      "confidence": {"X":cX, "Y":cY, "Z":cZ}
    }

If **all** axes have max(belief) ≥ τ, you should stop. Otherwise choose the next best view.
Note that you can revisit some views to stengthen your belief.

You should also decide which axes you want to focus on in a view. For example, if you choose a view that shows the XY plane, then you should focus on only the X axis and Y axis or even just focus on X or Y axis.

Note that the confidence score represents the reliability of the answer got from that view. Zero confidence score for a view indicates that the relative position is not clear revealed through that view.

**Rules**  
1. Wrap your internal reasoning in `<think>…</think>`  
2. Then emit exactly one `<answer>…</answer>` containing **only** this JSON:

{
  "action":  "CAPTURE"|"STOP",
  "view":    {"az": <number>, "el": <number>} | null,
  "axis":   ["X", "Y"]
}
No extra text or fields.
'''


LLM_FIRST_TURN = '''
# First turn (no belief_state or history)
Task: find (±X,±Y,±Z) for TARGET={target} vs CENTRAL={central}.  
Threshold τ = {tau}.

Propose your initial viewpoint.
Respond with:
<think>…</think>
<answer>{{
  "action": "CAPTURE",
  "view": {{"az": <num>, "el": <num>}},
  "axis": ["axes to focus on for this view"]
}}</answer>
'''

LLM_INTERMEDIATE_TURN = '''
# Subsequent turn
Threshold τ = {tau}
belief_state = {belief_state}
history      = {history}

Decide whether to STOP or pick another view.
Respond with:
<think>…</think>
<answer>{{
  "action":   "CAPTURE"|"STOP",
  "view":     {{"az": <num>, "el": <num>}} | null,
  "axis": ["axes to focus on for this view"] | null
}}</answer>
'''
