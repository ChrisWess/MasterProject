import * as d3 from "d3";
import {ZoomBehavior} from "d3";
import Box from '@mui/material/Box';
import {useNavigate, useOutletContext, useParams} from "react-router-dom";
import {FC, RefObject, useCallback, useEffect, useMemo, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import {ProjectStats} from "../api/models/project";
import {setProject} from "../reducers/mainPageSlice";
import {ImageDocument} from "../api/models/imgdoc";
import {setDoc, setImgUrl, setLabelMap} from "../reducers/idocSlice";
import NewObjectControlPanel from "./NewObjectControl";
import ImageAnnotator from "./image_labeling/BBoxImgAnnotator";
import {loadDocImage, loadProject} from "../document/ProjectIDocPage";
import {loadDoc} from "./ObjectPage";
import {mapLabels} from "../document/DocControl";
import {Label} from "../api/models/label";


const NewObjectPage: FC = () => {
    const {projectName, docId} = useParams();
    const context: any = useOutletContext();

    const navigate = useNavigate();
    const dispatch = useDispatch();
    // global state (redux)
    const project: ProjectStats | undefined = useSelector((state: any) => state.mainPage.currProject);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const labelsMap: [string, Label][] | undefined = useSelector((state: any) => state.iDoc.labelMap);

    const svgRef: RefObject<SVGSVGElement> = useRef<SVGSVGElement>(null);
    const rectRef: RefObject<SVGRectElement> = useRef<SVGRectElement>(null);

    // main zoom element
    const zoom: ZoomBehavior<SVGSVGElement, unknown> = useMemo(() =>
        d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.5, 5]), []);

    const resetZoom = useCallback(() => {
        const svg = d3.select<SVGSVGElement, unknown>(svgRef.current!);
        svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    }, [zoom, svgRef.current])

    const resetRect = useCallback(() => {
        const myRect = d3.select(rectRef.current);
        myRect.attr("width", 0).attr("height", 0);
    }, [rectRef.current]);

    useEffect(() => {
        if (!labelsMap) {
            mapLabels(idoc).then(lm => lm && dispatch(setLabelMap(lm)));
        }
    }, [idoc, labelsMap]);

    useEffect(() => {
        if (!projectName) {
            navigate('/notfound404')
        } else if (!project || project.title != projectName) {
            loadProject(projectName).then(projectData => projectData ?
                dispatch(setProject(projectData.result)) :
                navigate('/notfound404'))
        }
        if (!docId) {
            navigate('/notfound404')
        } else if (!idoc || idoc._id != docId) {
            loadDoc(docId).then(idocData => {
                if (idocData) {
                    let doc = idocData.result;
                    dispatch(setDoc(doc));
                    loadDocImage(docId).then(file => {
                        file && dispatch(setImgUrl(file))
                    });
                } else {
                    navigate('/notfound404')
                }
            })
        } else {
            dispatch(setDoc(idoc));
        }
        context.setControlPanel(<NewObjectControlPanel resetRect={resetRect} resetZoomCallback={resetZoom}/>)
    }, []);

    return (
        <Box height='100%'>
            <ImageAnnotator svgRef={svgRef} rectRef={rectRef} zoom={zoom} resetRect={resetRect} height={780}/>
        </Box>
    )
}

export default NewObjectPage
