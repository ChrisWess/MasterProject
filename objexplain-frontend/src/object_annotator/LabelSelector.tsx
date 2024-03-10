import {ChangeEvent, FC, useEffect, useState} from "react";
import Box from "@mui/material/Box";
import {Autocomplete, Button, Chip, Select, SelectChangeEvent, TextField} from "@mui/material";
import {useDispatch, useSelector} from "react-redux";
import {getRequest, postRequest, putRequest} from "../api/requests";
import {resetLabelMap} from "../reducers/idocSlice";
import Typography from "@mui/material/Typography";
import {Label} from "../api/models/label";
import {DetectedObject} from "../api/models/object";
import {setObjectLabel} from "../reducers/objectSlice";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import MenuItem from "@mui/material/MenuItem";
import {clearBbox} from "../reducers/objectCreateSlice";


interface LabelSelectProps {
    labelCaption: string;
    categoriesCaption: string;
    categoriesDescriptor: string;
    labelButtonText: string;
    makeNewObject: boolean;  // false := label update
    setAlertContent: Function;
    setAlertSeverity: Function;
    params?: any;
}

const LabelSelect: FC<LabelSelectProps> = ({
                                               labelCaption, categoriesCaption, categoriesDescriptor, labelButtonText,
                                               makeNewObject, setAlertContent, setAlertSeverity, ...params
                                           }) => {
    const [labelValue, setLabelValue] = useState<string>('');
    const [queriedLabels, setQueriedLabels] = useState<any[]>([]);
    const [categoryList, setCategoryList] = useState<string[]>();
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const newBbox: any | undefined = useSelector((state: any) => state.newObj.newBbox);

    const searchLabels = async (event: ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
        event.preventDefault()
        let input = event.target.value
        if (input.length > 2) {
            input = input.charAt(0).toUpperCase() + input.slice(1).toLowerCase();
            let data = await getRequest('label/search', undefined, {query: input})
            if (data) {
                let result = data.result
                setQueriedLabels(result.map((value: [string, string]) => {
                    return {id: value[0], label: value[1]}
                }));
            }
        } else {
            setQueriedLabels([]);
        }
        setLabelValue(input);
    }

    const fetchLabel = async (labelId: string) => {
        return await getRequest('label', labelId)
    }

    const handleUpdateLabel = async () => {
        if (labelValue && detObj) {
            let data;
            let objId = detObj._id;
            let valueIdx = queriedLabels.findIndex(value => value.label === labelValue);
            if (valueIdx === -1) {
                data = await postRequest('object/label/new', {objectId: objId, label: labelValue})
            } else {
                let newLabelId = queriedLabels[valueIdx].id;
                data = await putRequest('object/label', {objectId: objId, labelId: newLabelId})
            }
            if (data) {
                fetchLabel(data.result.updatedTo.objects.labelId).then(
                    label => label && dispatch(setObjectLabel(label)))
                setLabelValue('')
                dispatch(resetLabelMap())
            }
        }
    }

    const handleInsertObject = async () => {
        if (selectedCategories.length > 0) {
            if (labelValue && idoc && newBbox) {
                let data;
                let valueIdx = queriedLabels.findIndex(value => value.label === labelValue);
                if (valueIdx === -1) {
                    data = await postRequest('object', {
                        docId: idoc._id, labelName: labelValue, categories: selectedCategories,
                        bboxTlx: newBbox.tlx, bboxTly: newBbox.tly, bboxBrx: newBbox.brx, bboxBry: newBbox.bry
                    })
                } else {
                    let newLabelId = queriedLabels[valueIdx].id;
                    data = await postRequest('object', {
                        docId: idoc._id, labelId: newLabelId,
                        bboxTlx: newBbox.tlx, bboxTly: newBbox.tly, bboxBrx: newBbox.brx, bboxBry: newBbox.bry
                    })
                }
                if (data) {
                    fetchLabel(data.result.labelId).then(
                        label => label && dispatch(setObjectLabel(label)))
                    dispatch(resetLabelMap())
                    dispatch(clearBbox())
                    navigate(idoc.objects!.length.toString())
                }
            }
        } else {
            setAlertSeverity('error')
            setAlertContent('You need to specify at least one category!')
        }
        // TODO: show errors when failed
    }

    const deleteCategory = async () => {

    }

    const removeCategoryFromLabel = async () => {

    }

    useEffect(() => {
        if (makeNewObject) {
            getRequest('category').then(data => data ? setCategoryList(data.result) : navigate(''))
        }
    }, []);

    // TODO: if label was found with autocomplete, then optionally allow to add further categories to the label.
    //   if the label is new, it should be required for the user to select at least one category.

    return (
        <>
            <Typography sx={{mb: 0.5, pt: 1}}>{labelCaption}</Typography>
            <Box sx={{display: 'flex', mb: 1}}>
                <Autocomplete
                    options={queriedLabels} open={labelValue.length > 2} sx={{width: "80%"}}
                    renderInput={(params) =>
                        <TextField {...params} label="Input a label"
                                   onChange={(e) => searchLabels(e)}
                                   value={labelValue}
                                   sx={{
                                       "& .MuiOutlinedInput-notchedOutline": {
                                           borderColor: "#9090C0",
                                       }
                                   }}/>}
                />
                <Button
                    disabled={!newBbox || labelValue.length < 3 || selectedCategories.length == 0}
                    sx={{width: "20%"}} onClick={makeNewObject ? handleInsertObject : handleUpdateLabel}>
                    {labelButtonText}
                </Button>
            </Box>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <Typography sx={{pr: 1, my: 'auto'}}>{categoriesDescriptor}</Typography>
                <Select label="Category" disabled={!categoryList || categoryList.length == 0} sx={{flexGrow: 80}}
                        onChange={(event: SelectChangeEvent) => {
                            setSelectedCategories([...selectedCategories, event.target.value as string])
                        }}>
                    {categoryList?.map(category =>
                        <MenuItem value={category}>
                            {category.charAt(0).toUpperCase() + category.slice(1).toLowerCase()}
                        </MenuItem>)}
                </Select>
            </Box>
            <Typography sx={{mb: 0.5, pt: 1}}>{categoriesCaption}</Typography>
            <Box sx={{display: 'flex', mb: 2}}>
                {makeNewObject ?
                    selectedCategories.map((category, index) =>
                        <Chip key={'categ' + index} label={<b>{category}</b>} color='primary'
                              sx={{textShadow: '0px 0.5px 0px black', fontSize: '15px'}}
                              onDelete={removeCategoryFromLabel}/>) :
                    objectLabel && objectLabel.categories.map((category, index) =>
                        <Chip key={'categ' + index} label={<b>{category}</b>} color='primary'
                              sx={{textShadow: '0px 0.5px 0px black', fontSize: '15px'}}
                              onDelete={deleteCategory}/>)}
            </Box>
        </>
    )
}

export default LabelSelect
