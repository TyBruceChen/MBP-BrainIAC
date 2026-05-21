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



#### Acknowledgement: 
Created on May 21, By [TyBruce](https://github.com/TyBruceChen?tab=repositories)