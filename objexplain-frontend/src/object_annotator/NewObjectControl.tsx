import {ChangeEvent, FC, useState} from "react";
import Box from "@mui/material/Box";
import {Autocomplete, Button, ButtonGroup, Divider, IconButton, TextField} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {getRequest, postRequest, putRequest} from "../api/requests";
import {resetLabelMap} from "../reducers/idocSlice";
import {switchZooming} from "../reducers/objectCreateSlice";


const NewObjectControlPanel: FC = () => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();
    const [labelUpdValue, setLabelUpdValue] = useState<string>('');
    const [queriedLabels, setQueriedLabels] = useState<any[]>([]);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const isZooming: boolean = useSelector((state: any) => state.newObj.isZooming);
    const resetZoom: Function | undefined = useSelector((state: any) => state.newObj.zoomResetter);

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

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toImageView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}} variant='h5'>Create new Object"</Typography>
            <Divider sx={{my: 1}}/>
            <Typography sx={{mb: 0.5, pt: 1}}>Select Object Label and Categories</Typography>
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
            <Divider sx={{my: 1}}/>
            <ButtonGroup>
                <Button onClick={() => dispatch(switchZooming())} variant={isZooming ? "contained" : "outlined"}>
                    Zoom
                </Button>
                <Button onClick={() => resetZoom && resetZoom()} variant="outlined" sx={{ml: 2, flexShrink: 0}}>
                    Reset Zoom
                </Button>
            </ButtonGroup>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default NewObjectControlPanel
