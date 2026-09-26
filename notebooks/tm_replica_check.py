"""Offline pre-check of a Claim Summary Card design, before spending a browser training run.

Replicates Teachable Machine's image trainer: frozen MobileNetV2 (alpha 0.35, 224x224, ImageNet
weights, global average pooling) -> Dense(100, relu) -> Dense(3, softmax, no bias); Adam lr 0.001,
batch 16, 50 epochs; 15% of the training images held out as Teachable Machine does. Inputs are
scaled to [-1, 1] exactly like the exported model. Test cards are only scored, never trained on.

This is an estimate, not the deliverable: the real model is trained in the browser and evaluated
with notebooks/evaluate_gtm.py. Needs `pip install tensorflow` (not in requirements.txt).

Usage:
    python notebooks/tm_replica_check.py data/summary_cards data/claim_id_to_card_mapping.csv
    SEEDS=5 EPOCHS=50 python notebooks/tm_replica_check.py ...
"""
import os, sys, numpy as np, pandas as pd
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import tensorflow as tf
from PIL import Image, ImageOps
root = sys.argv[1]; mapping = pd.read_csv(sys.argv[2])
base = tf.keras.applications.MobileNetV2(input_shape=(224,224,3), alpha=0.35, include_top=False, weights="imagenet", pooling="avg")
CL = ["Valid Claim","Invalid Claim","Manual Review"]
def load(paths):
    X = np.stack([np.asarray(ImageOps.fit(Image.open(p).convert("RGB"), (224,224), Image.Resampling.LANCZOS), dtype=np.float32) for p in paths])
    return base.predict(X/127.5-1.0, batch_size=64, verbose=0)
def split(s):
    m = mapping[mapping.split==s]
    return load([os.path.join(root, r) for r in m.relative_path]), np.array([CL.index(c) for c in m.claim_class])
Xtr,ytr = split("train"); Xva,yva = split("val"); Xte,yte = split("test")
accs=[]
for seed in range(int(os.environ.get("SEEDS","3"))):
    tf.keras.utils.set_random_seed(seed)
    idx = np.random.permutation(len(Xtr)); cut = int(len(idx)*0.85)
    head = tf.keras.Sequential([tf.keras.layers.Input((Xtr.shape[1],)), tf.keras.layers.Dense(100, activation="relu", kernel_initializer="variance_scaling"), tf.keras.layers.Dense(3, activation="softmax", use_bias=False)])
    head.compile(tf.keras.optimizers.Adam(1e-3), "sparse_categorical_crossentropy", metrics=["accuracy"])
    head.fit(Xtr[idx[:cut]], ytr[idx[:cut]], epochs=int(os.environ.get("EPOCHS","50")), batch_size=16, verbose=0)
    va=(head.predict(Xva,verbose=0).argmax(1)==yva).mean(); te=(head.predict(Xte,verbose=0).argmax(1)==yte).mean()
    accs.append(te); print(f"seed {seed}: val {va:.3f} test {te:.3f}", flush=True)
print("mean test", np.mean(accs))
