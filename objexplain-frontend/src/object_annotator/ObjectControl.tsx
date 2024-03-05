import {FC, useEffect, useState} from "react";
import Box from "@mui/material/Box";
import {Divider, FormControlLabel, FormGroup, IconButton, Switch} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import AlertMessage from "../components/AlertMessage";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {switchObjectsVisible} from "../reducers/idocSlice";
import {Label} from "../api/models/label";


const ObjectControlPanel: FC = () => {
    const [alertContent, setAlertContent] = useState<string>();
    const [alertSeverity, setAlertSeverity] = useState<string>();
    const [objectLabel, setObjectLabel] = useState<Label>();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);

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
            <FormGroup row sx={{ml: 1}}>
                <FormControlLabel control={<Switch defaultChecked onChange={() => dispatch(switchObjectsVisible())}/>}
                                  label="Show Objects" sx={{mr: 6}}/>
            </FormGroup>
            <Divider sx={{my: 1}}/>
            <AlertMessage content={alertContent} setContent={setAlertContent} severity={alertSeverity}
                          displayTime={6000}/>
        </Box>
    )
}

export default ObjectControlPanel
