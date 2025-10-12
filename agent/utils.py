import random


def generate_jitter_offsets(m: int, r_az: float, r_el: float) -> list:
    """
    Generate m random jitter offsets within ±r_az, ±r_el degrees.
    Returns list of (daz, del) pairs.
    """
    offsets = []
    for _ in range(m):
        daz = random.uniform(-r_az, r_az)
        del_ = random.uniform(-r_el, r_el)
        offsets.append((daz, del_))
    return offsets


def format_message(sys_prompt, user_prompt):
    message = []
    if sys_prompt:
        message.append({"role": "system", "content": sys_prompt})
    if user_prompt:
        message.append({"role": "user", "content": user_prompt})
        
    return message
