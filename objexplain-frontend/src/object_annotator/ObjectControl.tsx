import {ChangeEvent, FC, useEffect, useMemo, useState} from "react";
import Box from "@mui/material/Box";
import {Autocomplete, Button, Chip, Divider, IconButton, List, ListItem, TextField} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {Label} from "../api/models/label";
import {getRequest, postRequest, putRequest} from "../api/requests";
import {resetLabelMap} from "../reducers/idocSlice";
import ListItemText from "@mui/material/ListItemText";


const ObjectControlPanel: FC = () => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();
    const [objectLabel, setObjectLabel] = useState<Label>();
    const [labelUpdValue, setLabelUpdValue] = useState<string>('');
    const [queriedLabels, setQueriedLabels] = useState<any[]>([]);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);

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
        setLabelUpdValue(input);
    }

    const handleUpdateLabel = async () => {
        if (labelUpdValue && idoc?.objects && objIdx !== undefined) {
            let data = undefined;
            let objId = idoc.objects[objIdx]._id;
            let valueIdx = queriedLabels.findIndex(value => value.label === labelUpdValue);
            if (valueIdx === -1) {
                data = await postRequest('object/label/new', {objectId: objId, label: labelUpdValue})
            } else {
                let newLabelId = queriedLabels[valueIdx].id;
                data = await putRequest('object/label', {objectId: objId, labelId: newLabelId})
            }
            if (data) {
                setLabelUpdValue('')
                dispatch(resetLabelMap())
            }
        }
    }

    const annoList = useMemo(() => {
        let objs = idoc?.objects;
        if (objs && objIdx !== undefined) {
            let annos = objs[objIdx].annotations
            return (<List className="annotations" key="annoList">
                {annos?.map((anno, index) =>
                    <ListItem divider key={'annoItem' + index}>
                        <ListItemText key={'annoText' + index}>
                            <Typography variant='h6' color='primary.light'>
                                {anno.text}
                            </Typography>
                        </ListItemText>
                    </ListItem>)}
            </List>)
        }
        return undefined
    }, [idoc])

    const toProjectView = () => {
        if (project) {
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toImageView = () => {
        if (project && idoc) {
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}`)
        }
    }

    const getMappedLabel = (labelId: string) => {
        if (labelsMap) {
            for (let i = 0; i < labelsMap.length; i++) {
                if (labelsMap[i][0] === labelId) {
                    return labelsMap[i][1]
                }
            }
        }
        return undefined
    }

    useEffect(() => {
        if (idoc && idoc.objects && objIdx != undefined) {
            let mappedLabel = getMappedLabel(idoc.objects[objIdx].labelId);
            setObjectLabel(mappedLabel);
        }
    }, [idoc, objIdx, labelsMap]);

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toImageView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}} variant='h5'>Object Label
                "{objectLabel?.name}"</Typography>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 0.5, pt: 1}}>Update Object Label</Typography>
            <Box sx={{display: 'flex'}}>
                <Autocomplete
                    options={queriedLabels}
                    open={labelUpdValue.length > 2}
                    sx={{width: "100%"}}
                    renderInput={(params) =>
                        <TextField {...params} label="Input a label"
                                   onChange={(e) => searchLabels(e)}
                                   value={labelUpdValue}
                                   sx={{
                                       "& .MuiOutlinedInput-notchedOutline": {
                                           borderColor: "#9090C0",
                                       }
                                   }}/>}
                />
                <Button disabled={labelUpdValue.length < 3}
                        onClick={handleUpdateLabel}>Update</Button>
            </Box>
            <Typography sx={{mb: 0.5, pt: 1}}>Categories</Typography>
            <Box sx={{display: 'flex', mb: 2}}>
                {objectLabel && objectLabel.categories.map((category, index) =>
                    <Chip key={'categ' + index} label={<b>{category}</b>} color='primary'
                          sx={{textShadow: '0px 0.5px 0px black', fontSize: '15px'}}
                          onDelete={() => {
                          }}/>)}
            </Box>
            <Divider/>
            {!!annoList && annoList}
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default ObjectControlPanel
