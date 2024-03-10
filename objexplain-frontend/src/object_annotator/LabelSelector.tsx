import {FC, useEffect, useState} from "react";
import Box from "@mui/material/Box";
import {Autocomplete, Button, Chip, Select, SelectChangeEvent, TextField} from "@mui/material";
import {useDispatch, useSelector} from "react-redux";
import {deleteRequest, getRequest, postRequest, putRequest} from "../api/requests";
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
    categoryButtonText: string;
    makeNewObject: boolean;  // false := label update
    setAlertContent: Function;
    setAlertSeverity: Function;
    params?: any;
}

const LabelSelect: FC<LabelSelectProps> = ({
                                               labelCaption,
                                               categoriesCaption,
                                               categoriesDescriptor,
                                               labelButtonText,
                                               categoryButtonText,
                                               makeNewObject,
                                               setAlertContent,
                                               setAlertSeverity,
                                               ...params
                                           }) => {
    const [labelValue, setLabelValue] = useState<string>('');
    const [labelIdx, setLabelIdx] = useState<number>();
    const [queriedLabels, setQueriedLabels] = useState<any[]>([]);
    const [categoryList, setCategoryList] = useState<string[]>();
    const [category, setCategory] = useState<string>('');
    const [assignedCategories, setAssignedCategories] = useState<string[]>([]);
    const [selectedCategories, setSelectedCategories] = useState<string[]>([]);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const objectLabel: Label | undefined = useSelector((state: any) => state.object.objectLabel);
    const newBbox: any | undefined = useSelector((state: any) => state.newObj.newBbox);

    const searchLabels = async (event: any, value?: any) => {
        event.preventDefault()
        let queryLabels;
        let stringInput: string;
        if (value) {
            stringInput = value.lower;
        } else {
            stringInput = event.target.value;
        }
        if (stringInput.length > 2) {
            let data = await getRequest('label/search', undefined,
                {query: stringInput.toLowerCase()})
            if (data) {
                let result = data.result
                queryLabels = result.map((value: [string, string]) => {
                    return {id: value[0], label: value[1], lower: value[1].toLowerCase()}
                });
            }
        } else {
            queryLabels = [];
        }
        setLabelValue(stringInput);
        return {result: queryLabels, value: stringInput}
    }

    const fetchLabelCategories = async (queryResult: any) => {
        let labelList: any[] = queryResult.result;
        let valueIdx = labelList.findIndex(value => value.lower === queryResult.value.toLowerCase());
        if (valueIdx >= 0) {
            let match = labelList[valueIdx];
            if (makeNewObject) {
                getRequest('label', match.id, {categories: 1}).then(
                    data => data && setAssignedCategories(data.result.categories))
            }
            setLabelIdx(valueIdx)
        } else if (labelIdx !== undefined && labelIdx >= 0) {
            setLabelIdx(undefined)
            if (makeNewObject) {
                setAssignedCategories([])
            }
        }
        setQueriedLabels(labelList);
    }

    const fetchLabel = async (labelId: string) => {
        return await getRequest('label', labelId)
    }

    const handleUpdateLabel = async () => {
        if (detObj && objectLabel) {
            let data = undefined;
            if (labelValue) {
                let objId = detObj._id;
                // TODO: save the label index in a state, if the input matches a label in the list
                let valueIdx = queriedLabels.findIndex(value => value.lower === labelValue);
                if (valueIdx === -1) {
                    data = await postRequest('object/label/new', {objectId: objId, label: labelValue})
                } else {
                    let newLabelId = queriedLabels[valueIdx].id;
                    if (newLabelId === objectLabel._id) {
                        if (selectedCategories.length !== 0) {
                            // TODO: add selected category
                        }
                    } else {
                        data = await putRequest('object/label',
                            {objectId: objId, labelId: newLabelId})
                    }
                }
                if (data) {
                    fetchLabel(data.result.updatedTo.objects.labelId).then(
                        label => label && dispatch(setObjectLabel(label)))
                    setLabelValue('')
                    dispatch(resetLabelMap())
                }
            } else {

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

    const deleteCategory = async (category: string) => {
        if (objectLabel) {
            let categoryIdx: number = objectLabel.categories.indexOf(category)
            if (categoryIdx == -1) {
                setAlertSeverity('error')
                setAlertContent('The category that you are trying to delete is not linked to the current label!')
            } else {
                deleteRequest('category/' + category, objectLabel._id).then(data => {
                    if (data) {
                        objectLabel.categories.splice(categoryIdx, 1);
                        dispatch(setObjectLabel(objectLabel));
                    } else {
                        setAlertSeverity('error')
                        setAlertContent('Error while deleting the category in the database!')
                    }
                })
            }
        }
    }

    const removeCategoryFromLabel = (categoryIdx: number) => {
        let categories: string[] = [...selectedCategories.slice(0, categoryIdx),
            ...selectedCategories.slice(categoryIdx + 1)]
        setSelectedCategories(categories)
    }

    const addSelectedCategory = (event: SelectChangeEvent) => {
        let categ: string = event.target.value
        setCategory(categ)
        setSelectedCategories([...selectedCategories, categ])
    }

    const setSelectedCategory = (event: SelectChangeEvent) => {
        setCategory(event.target.value as string)
    }

    useEffect(() => {
        if (makeNewObject) {
            getRequest('category').then(data => data ? setCategoryList(data.result) : navigate(''))
        }
    }, []);

    // TODO: make the category select also a autocomplete box that allows adding new categories

    return (
        <>
            <Typography sx={{mb: 0.5, pt: 1}}>{labelCaption}</Typography>
            <Box sx={{display: 'flex', mb: 1}}>
                <Autocomplete
                    freeSolo
                    onChange={(e, value) =>
                        searchLabels(e, value).then(result => fetchLabelCategories(result))
                    }
                    options={queriedLabels} open={labelValue.length > 2} sx={{width: "70%"}}
                    renderInput={(params) =>
                        <TextField {...params} label="Input a label"
                                   onChange={(e) =>
                                       searchLabels(e).then(result => fetchLabelCategories(result))
                                   }
                                   value={labelValue}
                                   sx={{
                                       "& .MuiOutlinedInput-notchedOutline": {
                                           borderColor: "#9090C0",
                                       }
                                   }}/>}
                />
                <Button
                    disabled={makeNewObject ? !newBbox || labelValue.length < 3 || selectedCategories.length == 0 :
                        labelValue.length < 3 && selectedCategories.length == 0}
                    sx={{width: "30%"}} onClick={makeNewObject ? handleInsertObject : handleUpdateLabel}>
                    {labelButtonText}
                </Button>
            </Box>
            <Typography sx={{mb: 0.5}}>{categoriesDescriptor}</Typography>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <Typography sx={{pr: 1, my: 'auto'}}>Add Category: </Typography>
                <Select label="Category" disabled={!categoryList || categoryList.length == 0} sx={{flexGrow: 80}}
                        onChange={makeNewObject ? addSelectedCategory : setSelectedCategory}
                        value={category}>
                    {categoryList?.map(categ =>
                        <MenuItem key={'select-' + categ} value={categ}>
                            {categ.charAt(0).toUpperCase() + categ.slice(1).toLowerCase()}
                        </MenuItem>)}
                </Select>
                <Button disabled={false} sx={{width: "30%"}}>
                    {categoryButtonText}
                </Button>
            </Box>
            <Typography sx={{mb: 0.5, pt: 1}}>{categoriesCaption}</Typography>
            <Box sx={{display: 'flex', mb: 2, border: '1px solid #080808', minHeight: 30, p: 1}}>
                {makeNewObject ?
                    <>
                        {assignedCategories.map((category, index) =>
                            <Chip key={'categ' + index} label={<b>{category}</b>}
                                  sx={{textShadow: '0px 0.5px 0px black', fontSize: '15px', bgcolor: '#672400'}}
                                  onDelete={() => deleteCategory(category)}/>)}
                        {selectedCategories.map((category, index) =>
                            <Chip key={'newCateg' + index} label={<b>{category}</b>} color='primary'
                                  sx={{textShadow: '0px 0.5px 0px black', fontSize: '15px'}}
                                  onDelete={() => removeCategoryFromLabel(index)}/>)}
                    </> :
                    objectLabel && objectLabel.categories.map((category, index) =>
                        <Chip key={'categ' + index} label={<b>{category}</b>} color='primary'
                              sx={{textShadow: '0px 0.5px 0px black', fontSize: '15px'}}
                              onDelete={() => deleteCategory(category)}/>)}
            </Box>
        </>
    )
}

export default LabelSelect
