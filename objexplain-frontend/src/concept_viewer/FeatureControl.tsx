import {FC, useEffect, useMemo} from "react";
import Box from "@mui/material/Box";
import {
    Button,
    ButtonGroup,
    Divider,
    FormControlLabel,
    FormGroup,
    IconButton,
    List,
    ListItem,
    ListItemIcon,
    Switch
} from "@mui/material";
import ArrowLeftIcon from '@mui/icons-material/ArrowLeft';
import ArrowDropUpIcon from '@mui/icons-material/ArrowDropUp';
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import Typography from "@mui/material/Typography";
import {useNavigate} from "react-router-dom";
import {ImageDocument} from "../api/models/imgdoc";
import {BoundingBoxCoords} from "../api/models/feature";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import {addBbox, switchBboxVisible, toggleObjMovable, toggleShowPrevBboxs} from "../reducers/featureSlice";


interface FeatureControlProps {
    resetZoomCallback: Function;
}

const FeatureControlPanel: FC<FeatureControlProps> = ({resetZoomCallback}) => {
    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const objIdx: number | undefined = useSelector((state: any) => state.object.objIdx);
    const annoIdx: number | undefined = useSelector((state: any) => state.annotation.annotationIdx);
    const conceptIdx: number | undefined = useSelector((state: any) => state.feature.conceptIdx);
    const currBbox: BoundingBoxCoords | undefined = useSelector((state: any) => state.feature.currBbox);
    const bboxs: BoundingBoxCoords[] = useSelector((state: any) => state.feature.bboxs);
    const bboxsVis: boolean[] = useSelector((state: any) => state.feature.bboxsVis);
    const showPrev: boolean = useSelector((state: any) => state.feature.showPrevInput);
    const isMoveObjImg: boolean = useSelector((state: any) => state.feature.isMoveObjImg);

    const toProjectView = () => {
        if (project) {
            navigate('/project/' + encodeURIComponent(project.title))
        }
    }

    const toAnnotationView = () => {
        if (project && idoc && objIdx !== undefined && annoIdx !== undefined) {
            navigate(`/project/${encodeURIComponent(project.title)}/idoc/${idoc._id}/${objIdx}/${annoIdx}`)
        }
    }

    const deleteFeature = (idx: number) => {
        console.log('Delete Feature ' + idx)
    }

    const bboxList = useMemo(() => {
        if (bboxs) {
            return <List className="bboxs" key="bboxsList">
                {bboxs.map((bbox, index) => {
                    return <ListItem divider key={'bboxItem' + index}>
                        <ListItemButton key={'bboxButt' + index} sx={{py: 0}}>
                            <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'bboxIcon' + index}>
                                {index + 1}
                            </ListItemIcon>
                            <ListItemText key={'bboxText' + index}>
                                <Typography sx={{fontSize: '14pt', color: 'text.secondary'}}>
                                    Bounding Box <b>{index + 1}</b>
                                </Typography>
                            </ListItemText>
                        </ListItemButton>
                        <ListItemIcon>
                            <IconButton onClick={() => dispatch(switchBboxVisible(index))}
                                        sx={{color: 'text.secondary'}}>
                                {bboxsVis[index] ?
                                    <VisibilityOffOutlinedIcon/> :
                                    <VisibilityOutlinedIcon/>}
                            </IconButton>
                            <IconButton aria-label="comment" onClick={() => deleteFeature(index)}>
                                <DeleteIcon sx={{color: 'text.secondary'}}/>
                            </IconButton>
                        </ListItemIcon>
                    </ListItem>
                })}
            </List>
        }
        return <></>
    }, [bboxs, bboxsVis])

    useEffect(() => {

    }, []);

    return (
        <Box sx={{height: '100%', overflow: 'auto'}}>
            <Box sx={{display: 'flex', mb: 0.5}}>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toAnnotationView}>
                    <ArrowLeftIcon sx={{fontSize: 30, ml: -1}}/> Back</IconButton>
                <IconButton sx={{fontSize: 16, width: 140, color: 'secondary.dark'}} onClick={toProjectView}>
                    <ArrowDropUpIcon sx={{fontSize: 30, ml: -1}}/> Project</IconButton>
            </Box>
            <Typography sx={{mb: 1, color: 'text.secondary'}}
                        variant='h5'>Concept {conceptIdx === undefined ? -1 : conceptIdx + 1}</Typography>
            <FormGroup row sx={{ml: 1}}>
                <FormControlLabel control={<Switch checked={showPrev}
                                                   onChange={() => dispatch(toggleShowPrevBboxs())}/>}
                                  label="Show Features"/>
            </FormGroup>
            <Button disabled={!currBbox} variant='outlined'
                    sx={{width: '100%', textTransform: 'none'}}
                    onClick={() => dispatch(addBbox())}>
                Add Bounding Box to Feature
            </Button>
            <Divider sx={{my: 1}}/>
            <ButtonGroup sx={{width: '100%', bottom: 5}}>
                <Button onClick={() => dispatch(toggleObjMovable())} variant={isMoveObjImg ? "contained" : "outlined"}
                        sx={{flexGrow: 50}}>
                    Move / Zoom in Image
                </Button>
                <Button onClick={() => resetZoomCallback()} variant="outlined" sx={{ml: 2, flexGrow: 50}}>
                    Reset Image Position
                </Button>
            </ButtonGroup>
            <Divider sx={{mt: 3}}/>
            <Box sx={{overflow: 'auto', maxHeight: 300}}>{bboxList}</Box>
        </Box>
    )
}

export default FeatureControlPanel
