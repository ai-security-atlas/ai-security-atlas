import time, numpy as np, torch, labkit
labkit.banner()
import bd, vision_zoo as vz
from torch import nn
from art.estimators.classification import PyTorchClassifier
from art.defences.detector.poison import ActivationDefence
for kind in list(bd.KINDS) + ["clean"]:
    p = bd.poisoned_split(kind if kind!="clean" else "badnets"); idx = set(p["poison_idx"].tolist())
    x = p["x_train"].numpy(); yl = p["y_train"].numpy(); y = np.eye(10)[yl]
    m = bd.model(kind if kind!="clean" else bd.CLEAN)
    for q in m.parameters(): q.requires_grad_(True)
    pr = bd.Probe(m)
    clf = PyTorchClassifier(model=pr, loss=nn.CrossEntropyLoss(), optimizer=torch.optim.Adam(pr.parameters(), lr=1e-3), input_shape=(1,8,8), nb_classes=10, clip_values=(0.,1.), device_type="cpu")
    truth = np.array([i in idx for i in range(len(x))])
    vz.deterministic(0)
    t=time.time()
    ac = ActivationDefence(clf, x, y, ex_re_threshold=1.0)
    rep, clean = ac.detect_poison(nb_clusters=2, nb_dims=10, reduce="PCA", cluster_analysis="smaller")
    fl = np.array(clean)==0
    print(kind, f"{time.time()-t:.1f}s flagged", fl.sum(), "tp", (fl&truth).sum(), "per class", np.bincount(yl[fl],minlength=10).tolist())
    for c in range(10):
        for k,v in rep[f"Class_{c}"].items():
            if "ExRe_Score" in v: print("   class",c,k,v)
