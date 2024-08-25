import numpy as np
import torch
from PIL import ImageDraw, ImageFont
from bson import ObjectId
from torch.nn.functional import interpolate
from torch.utils.data import DataLoader
from torchvision.transforms import v2
from torchvision.transforms.v2.functional import adjust_brightness

from app.autoxplain.model import ccnn_net, dset, oxp_model_data_dir, oxp_root_dir, model_save_dir

center_crop = v2.Compose([
    v2.PILToTensor(),
    v2.ToDtype(torch.uint8),
    v2.CenterCrop(size=(448, 448))
])

to_pil = v2.ToPILImage()


def _pil_imgs_to_tensor(imgs):
    if torch.is_tensor(imgs):
        return imgs
    if not imgs:
        return
    img_preproc = dset.load_torch_image_resized if isinstance(imgs[0], ObjectId) else center_crop
    if len(imgs) == 1:
        imgs = img_preproc(imgs[0])
        return imgs if dset.preprocess_transforms is None else dset.preprocess_transforms(imgs)
    else:
        if dset.preprocess_transforms is None:
            imgs = [img_preproc(img) for img in imgs]
        else:
            imgs = [dset.preprocess_transforms(img_preproc(img)) for img in imgs]
        return torch.stack(imgs)


def classify_object_images(imgs, confidence_thresh=0.):
    preds, confs = ccnn_net.infer(_pil_imgs_to_tensor(imgs))
    return [y.item() if conf.item() > confidence_thresh else None for y, conf in zip(preds, confs)]


def identify_object_concepts(imgs):
    cidxs_batches, confidences = ccnn_net.find_top_concept_idxs(_pil_imgs_to_tensor(imgs))
    results = []
    for row, conf in zip(cidxs_batches, confidences):
        concept_strs = []
        with open(oxp_model_data_dir / 'unique_concepts.txt', 'r') as f:
            lines = f.readlines()
            for idx in row:
                concept_strs.append(lines[idx][:-1])
        results.append((np.array(row), concept_strs, np.array(conf)))
    return results


def show_dset(num_sample=5):
    vds = dset.validation_dataset(False)
    sampler = torch.utils.data.sampler.BatchSampler(torch.utils.data.sampler.RandomSampler(vds),
                                                    batch_size=1, drop_last=False)
    tdl = DataLoader(vds, sampler=sampler)
    for i, x in enumerate(tdl, start=1):
        to_pil(x[0].squeeze()).show()
        if i == num_sample:
            return


def _get_mask_text_location(interpolated_mask, text_len, font_size, padding=10):
    # FIXME
    text_cols = text_len * font_size / 2
    ncols = interpolated_mask.shape[0]
    padded_text_cols = text_cols + padding
    col_limit = ncols - padded_text_cols
    assert col_limit > 0, "The font size is too large!"
    padded_text_rows = font_size + padding
    text_rows_xy_padded = padded_text_rows + padding
    is_mask_located_top = torch.any(interpolated_mask[:text_rows_xy_padded]).item()
    top_to_bottom = True
    rows_iter = torch.any(interpolated_mask, dim=0)  # check rows from left to right
    if is_mask_located_top:
        is_mask_located_bottom = torch.any(interpolated_mask[-text_rows_xy_padded:]).item()
        if is_mask_located_bottom and torch.any(interpolated_mask[:, :padded_text_cols + padding]).item():
            return padding, padding
        else:
            rows_iter = reversed(rows_iter)
            top_to_bottom = False
    x_pos = padding
    row = 0
    was_masked = False
    for row, is_masked in enumerate(rows_iter):
        if not was_masked and is_masked:
            was_masked = True
            continue
        elif was_masked and not is_masked:
            row = row - 1 if top_to_bottom else interpolated_mask.shape[1] - row - 1
        else:
            continue
        for col, bval in enumerate(interpolated_mask[row]):
            if bval or col > col_limit:
                x_pos = col
                break
        break
    row = np.minimum(row, interpolated_mask.shape[1])
    row = row - padded_text_rows if top_to_bottom else row + padding
    return np.minimum(x_pos, padding), np.maximum(row, padding)


def _simple_mask_text_location(interpolated_mask, font_size, padding=10):
    padded_text_rows = 2 * font_size + 2 * padding
    is_mask_located_top = torch.any(interpolated_mask[:padded_text_rows]).item()
    row = interpolated_mask.shape[0] - 2 * font_size - padding if is_mask_located_top else padding
    return padding, row


def highlight_filter_activation_masks(obj_ids, concept_data, mask_thresh=0.95, font_size=18, show_local=False):
    # Create a binary mask where activation values greater than 0.95 (threshold => mask_thresh)
    # of the maximum activation are set to 1, and the rest are set to 0.
    # Then we use bilinear interpolation to generate the image-resolution mask,
    # and overlay the mask on an image to identify the receptive field.
    result = []
    highlighted_img_dir = model_save_dir / 'highlighted_imgs'
    highlighted_img_dir.mkdir(exist_ok=True)
    img_label_font = ImageFont.truetype(str(oxp_root_dir / "fonts/AbhayaLibre.ttf"), font_size)
    imgs = _pil_imgs_to_tensor(obj_ids)
    fms = ccnn_net.get_concept_feature_maps(imgs)
    for obj_id, imgf, concepts in zip(obj_ids, fms, concept_data):
        img = dset.load_torch_image(obj_id)  # load base image to overlay with the interpolated mask
        imgs_concepts_marked = []
        for i, (concept_filter_idx, concept_name, confidence) in enumerate(zip(*concepts), start=1):
            img_fpath = highlighted_img_dir / f'{obj_id}_top{i}c.png'
            concept_filter_map = imgf[concept_filter_idx]  # resulting feature map from this filter
            max_activation = torch.max(concept_filter_map).item()
            mask = concept_filter_map >= max_activation * mask_thresh
            interp_mask = torch.reshape(mask, (1, 1, *mask.shape)).to(dtype=torch.float32)
            # interpolate the mask to fit to image size and invert mask in order to apply visual update
            interp_mask = interpolate(interp_mask, img.shape[1:3], mode='bilinear').squeeze().to(dtype=bool)
            mask_loc = _simple_mask_text_location(interp_mask, font_size)
            interp_mask = interp_mask.expand_as(img)
            darker_img = adjust_brightness(img, 0.5)
            darker_img[interp_mask] = img[interp_mask]
            masked_img = to_pil(darker_img)
            # Label the image with the concept description (i.e. its name)
            concept_name = ' '.join(map(lambda s: s.capitalize(), concept_name.split()))
            concept_name += f' ({100 * confidence:0.1f}%)'
            ImageDraw.Draw(masked_img).text(mask_loc, concept_name, (255, 255, 255), font=img_label_font)
            if show_local:
                masked_img.show()
            masked_img.save(img_fpath)
            imgs_concepts_marked.append(masked_img)
        result.append(imgs_concepts_marked)
    return result


def generate_full_annotation_data(img, mask_thresh=0.95):
    # TODO: handle new parameter that allows inputting all concept indices from all annotations for the image
    #  in order to create a bounding box for all these occurring concepts.
    #  This requires mapping an explanation's concept to the best matching feature map index.
    orig_img_size = img.size
    img = dset.preprocess_single_pil_img(img)
    fms, cls_idx, _, con_idxs, _ = ccnn_net.infer_complete(img)  # omit confidence values
    cls_idx = cls_idx.item()
    con_idxs = con_idxs.squeeze()
    fms = fms.squeeze()
    concept_list = []
    with open(oxp_model_data_dir / 'unique_concepts.txt', 'r') as f:
        lines = f.readlines()
        for idx in con_idxs:
            concept_words = lines[idx][:-1].split(' ')
            concept_list.append(concept_words)
    # Create a feature bounding box
    bboxs = []
    for idx in con_idxs:
        concept_filter_map = fms[idx]  # resulting feature map from this filter
        max_activation = torch.max(concept_filter_map).item()
        mask = concept_filter_map >= max_activation * mask_thresh
        interp_mask = torch.reshape(mask, (1, 1, *mask.shape)).to(dtype=torch.float32)
        # interpolate the mask to fit to image size and invert mask in order to apply visual update
        interp_mask = interpolate(interp_mask, orig_img_size, mode='bilinear').squeeze().to(dtype=bool)
        lx = orig_img_size[0]
        ty = rx = by = -1
        for ridx, row in enumerate(interp_mask.T):
            if row.sum().item() > 0:
                if ty == -1:
                    ty = ridx
                by = ridx
                for cidx, bit in enumerate(row):
                    if bit == 1:
                        lx = min(lx, cidx)
                        rx = max(rx, cidx)
        if ty == -1 or rx == -1:
            bboxs.append(None)
        else:
            bboxs.append((lx, ty, rx, by))
    assert len(bboxs) == len(concept_list)
    return cls_idx, concept_list, bboxs
