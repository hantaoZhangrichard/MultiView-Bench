import math


class BeliefState:
    def __init__(self, lam: float = 1.0, gamma: float = 1.0, method: str = 'wilson'):
        # Dirichlet priors alpha[A][s]
        self.alpha = {A: {'+': lam, '0': lam, '-': lam} for A in ['X','Y','Z']}
        self.lam = lam
        self.gamma = gamma
        self.method = method

    def _wilson_neff(self, counts: dict) -> float:
        # Effective sample size
        kplus, kzero, kminus = counts['+'], counts['0'], counts['-']
        n = kplus + kzero + kminus
        if n == 0:
            return 0.0, 0.0
        kmax = max(kplus, kzero, kminus)
        phat = kmax / n
        z = 1.96
        lb = (phat + z*z/(2*n) - z * math.sqrt((phat*(1-phat))/n + (z*z)/(4*n*n)))
        lb /= (1 + z*z/n)

        confidence = max(0.0, (max(lb, 1/3) - 1/3)/(2/3))**self.gamma

        # Effective sample size scaled by confidence
        neff = n * confidence
        return neff, confidence

    def _entropy_neff(self, counts: dict) -> float:
        kplus, kzero, kminus = counts['+'], counts['0'], counts['-']
        n = kplus + kzero + kminus
        if n == 0:
            return 0.0, 0.0
        p = [(counts[s] + self.lam)/(n + 3*self.lam) for s in ['+','0','-']]
        H = -sum(pi * math.log(pi) for pi in p)
        Hmax = math.log(3)

        confidence = ((1 - H/Hmax) ** self.gamma)
        neff = n * confidence
        return neff, confidence

    def update(self, axis_counts: dict):
        """
        axis_counts: {'X':{'+':k,'0':k,'-':k}, 'Y':..., 'Z':...}
        Updates Dirichlet alpha with effective counts.
        """
        confidence_scores = {}
        for A in ['X', 'Y', 'Z']:
            counts = axis_counts[A]
            if self.method == 'wilson':
                neff, confidence = self._wilson_neff(counts)
            else:
                neff, confidence = self._entropy_neff(counts)
            
            confidence_scores[A] = confidence

            # smooth proportions
            n = sum(counts.values())
            if n > 0 and neff > 0:
                p_hat = {s: (counts[s] + self.lam)/(n + 3*self.lam) for s in ['+', '0', '-']}
                for s in ['+', '0', '-']:
                    self.alpha[A][s] += neff * p_hat[s]

        return confidence_scores

    def get_posterior(self) -> dict:
        """Returns posterior mean P(A)[s]."""
        post = {}
        for A in ['X', 'Y', 'Z']:
            ssum = sum(self.alpha[A].values())
            post[A] = {s: self.alpha[A][s]/ssum for s in ['+','0','-']}
        return post

    def get_decision(self):
        post = self.get_posterior()
        decision = {}
        top_ps = {}
        for A in ['X', 'Y', 'Z']:
            probs = post[A]
            top_s, top_p = max(probs.items(), key=lambda x: x[1])
            decision[A] = top_s
            top_ps[A] = top_p
        return decision, top_ps

    def should_stop(self, tau: float = 0.9, kappa_min: float = 10) -> (bool, dict):
        """
        Returns (stop_flag, decision_labels)
        stop if top-prob ≥ tau AND alpha-sum ≥ kappa_min for all axes.
        """
        decision, top_ps = self.get_decision()
        ok = True
        for A in ['X', 'Y', 'Z']:
            top_p = top_ps[A]
            if not (top_p >= tau and sum(self.alpha[A].values()) >= kappa_min):
                ok = False
        return ok, decision