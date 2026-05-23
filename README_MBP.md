## Info

Dataset: [Maternal Brain Project](https://openneuro.org/datasets/ds005299/versions/1.0.0)

Preprocessing:
```
python src/preprocessing/mri_preprocess_3d_simple.py \ 
--temp_img src/preprocessing/atlases/temp_head.nii.gz  \
--input_dir data/unprocessed_T1w --output data/processed/
```

CSV guide file generation:
```
python src/utils/generate_brainiac_csv.py data/processed/temp_registered/ data/guide.csv
```


## Result

Results are put in [src/notes_book](src/notes_book) folder/repo.
- features.csv: raw features extracted from BrainIAC ViT
- features_pca.csv: merged features from PCA (PC1 - PC10)
- pca_lr_knn_kmeans_opticalflow.ipynb: LR, KNN, K-means used to fitting / clustering the data, and generate optical flow visualization
- output/*html: optical flow visualization compared different K-means centered points between different clusters

#### Acknowledgement: 
Created on May 21, By [TyBruce](https://github.com/TyBruceChen?tab=repositories)