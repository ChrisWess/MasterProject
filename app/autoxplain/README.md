# Comprehensible CNN: Training Setup Summary

## Data Preprocessing:
- Compute the tf-idf scores for all concepts (and order them).
- Filter all concepts that map some adjectives to the subject as a whole.
- Filter any concept that occurs in more than 20% of all classes.
- Select only concepts that have less than 50% of words in common compared to all previously selected concepts.
- Stop selecting concepts when the top 3 (or 4) concepts  have been selected as top descriptors of a label class.

## Model Setup:
- Pretrained VGG16 Convolutions used as the base feature extractor (ResNet 101 could optionally be used as well).
- 
