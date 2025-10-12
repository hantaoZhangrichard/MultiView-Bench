import json
import logging
from prompts import VLM_SYSTEM_PROMPT, VLM_USER_PROMPT, LLM_SYSTEM_PROMPT, LLM_FIRST_TURN, LLM_INTERMEDIATE_TURN
from utils import generate_jitter_offsets, format_message
from belief_state import BeliefState
from api_call_gpt import call_llm, call_vlm
from api_call_gemini import call_llm, call_vlm
from verifier import parse_answer, parse_answer_json


logging.basicConfig(
    filename='agent.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


class Agent:
    def __init__(self, model_name, tau: float = 0.9, kappa_min: float = 10):
        self.belief = BeliefState()
        self.history = []
        self.model_name = model_name
        self.tau = tau
        self.kappa_min = kappa_min
        self.steps = 1

    def propose_view(self, central: str, target: str) -> dict:
        # Create system prompt
        sys_prompt = LLM_SYSTEM_PROMPT

        # Create user prompt based on history
        if not self.history:
            user_prompt = LLM_FIRST_TURN.format(
                target=target, 
                central=central, 
                tau=self.tau
            )
        else:
            # Build state for intermediate turns
            belief_state = self.belief.get_posterior()
            user_prompt = LLM_INTERMEDIATE_TURN.format(
                tau=self.tau,
                belief_state=json.dumps(belief_state),
                history=json.dumps(self.history)
            )

        # Format messages and call LLM
        messages = format_message(sys_prompt, user_prompt)
        response = call_llm(messages, model_name=self.model_name)
        return response

    def perceive(self, img_path, central: str, target: str, focus_axis):
        user_prompt = VLM_USER_PROMPT.format(
                target=target, 
                central=central, 
            )
        sys_prompt = VLM_SYSTEM_PROMPT.format(
            axis=focus_axis,
            target_object=target, 
            central_object=central,)
        messages = format_message(sys_prompt, user_prompt)
        response = call_vlm(messages, image_path=img_path, model_name=self.model_name)
        return response

    def run(self, central: str, target: str, env, jitter_size, max_steps=10) -> str:
        """
        Main loop: propose clusters, jitter, measure, update belief.
        Returns final answer string.
        """
        while self.steps < max_steps:
            logging.info(f"Step: {self.steps} -------------------------------------")

            logging.info("LLM proposal ---------------------------------------")
            llm_response = self.propose_view(central, target)
            logging.info(llm_response)
            action = parse_answer_json(llm_response)
            if action['action'] == 'STOP':
                break

            # extract cluster plan
            az = action['view']['az']
            el = action['view']['el']

            focus_axis = action["axis"]

            offsets = generate_jitter_offsets(m=jitter_size, r_az=3, r_el=3)
            # Collect VLM votes
            axis_counts = {'X': {'+': 0, '0': 0, '-': 0}, 'Y': {'+': 0, '0': 0, '-': 0}, 'Z': {'+': 0, '0': 0, '-': 0}}
            for daz, del_ in offsets + [(0, 0)]:
                img_path = env.capture(az + daz, el + del_)
                ans = self.perceive(img_path=img_path, central=central, target=target, focus_axis=focus_axis)
                logging.info(f"VLM: {ans}")
                # parse e.g. <answer>(+X, -Y, 0Z)</answer>
                labels = parse_answer(ans)
                for axis, sign in labels.items():
                    axis_counts[axis][sign] += 1
                if daz == 0 and del_ == 0:
                    view_ans = labels
            logging.info("VLM results -------------------------------------------------")
            logging.info(axis_counts)

            # update belief
            confidence_scores = self.belief.update(axis_counts)
            logging.info("Condidence scores ------------------------------------------")
            logging.info(confidence_scores)
            # record history
            self.history.append({
                "step": self.steps,
                "view":   {"az": az, "el": el},
                "answer": view_ans,
                "confidence": confidence_scores
            })

            logging.info("History so far----------------------------------------------")
            logging.info(self.history)

            self.steps += 1

            # check stop
            stop, decision = self.belief.should_stop(self.tau, self.kappa_min)
            if stop:
                break
        decision, top_ps = self.belief.get_decision()
        ans = f"<answer>({decision['X']+'X'}, {decision['Y']+'Y'}, {decision['Z']+'Z'})</answer>"
        return ans, top_ps
