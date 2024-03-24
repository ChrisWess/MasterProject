import {FC, useEffect, useMemo, useState} from "react";
import {Box, Divider, List, ListItem, ListItemIcon} from "@mui/material";
import Typography from "@mui/material/Typography";
import {Concept} from "../api/models/concept";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import AddIcon from "@mui/icons-material/Add";
import {getRequest, postRequest} from "../api/requests";
import {CorpusWord} from "../api/models/corpus";
import PhraseChip from "./PhraseChip";
import ButtonTextfield from "../components/ButtonTextfield";
import {useDispatch, useSelector} from "react-redux";
import {addAdjective, addFullConcept, addNoun} from "../reducers/annotationCreateSlice";
import Button from "@mui/material/Button";


export const loadSuggestedConcepts = async () => {
    // TODO: temporary functionality for testing frontend (true impl should suggest based on selected object)
    return await getRequest('concept', undefined, {limit: 10})
}


export const loadSuggestedAdjectives = async () => {
    // TODO: temporary functionality for testing frontend
    return await getRequest('corpus/adjective', undefined, {limit: 15})
}


export const loadSuggestedNouns = async () => {
    // TODO: temporary functionality for testing frontend
    return await getRequest('corpus/noun', undefined, {limit: 15})
}


const ConceptsController: FC = () => {
    const [selectedConceptIdx, setSelectedConceptIdx] = useState<number>();
    const [conceptsUsed, setConceptsUsed] = useState<boolean[]>();
    const [concepts, setConcepts] = useState<Concept[]>();
    const [adjectives, setAdjectives] = useState<CorpusWord[]>();
    const [nouns, setNouns] = useState<CorpusWord[]>();

    const dispatch = useDispatch();
    const concNouns: string[][] = useSelector((state: any) => state.newAnno.nouns);

    const submitConceptClick = () => {
        if (selectedConceptIdx !== undefined && concepts && conceptsUsed && !conceptsUsed[selectedConceptIdx]) {
            dispatch(addFullConcept(concepts[selectedConceptIdx]))
            let usedConcepts = [...conceptsUsed];
            usedConcepts[selectedConceptIdx] = true;
            setConceptsUsed(usedConcepts);
            setSelectedConceptIdx(undefined);
        }
    }

    const suggestedConcepts = useMemo(() => {
        return (<List className="suggestedConcepts" key="suggestionList"
                      sx={{bgcolor: '#252525', p: 0}}>
            {concepts && conceptsUsed && concepts.map((concept, index) =>
                <ListItem divider key={'concSelectItem' + index}
                          sx={{
                              height: '40px',
                              bgcolor: (selectedConceptIdx !== undefined && selectedConceptIdx === index) ? '#405540' : ''
                          }}>
                    <ListItemButton key={'concSelectButt' + index} sx={{py: 0}}
                                    onClick={() => setSelectedConceptIdx(index)}
                                    disabled={conceptsUsed[index]}>
                        <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'concSelectIcon' + index}>
                            {index + 1}
                        </ListItemIcon>
                        <ListItemText key={'concSelectText' + index}>
                            <Typography variant='h6' color='primary.light'>
                                <b>{concept.phraseWords.join(' ')}</b>
                            </Typography>
                        </ListItemText>
                        <ListItemIcon>
                            <AddIcon sx={{color: 'text.primary'}}/>
                        </ListItemIcon>
                    </ListItemButton>
                </ListItem>)}
            <ListItemButton key={'conceptLoader'} sx={{py: 0, height: '40px'}} onClick={() => {
            }}>
                <ListItem divider key={'conceptLoadItem'} sx={{height: '40px'}}>
                    <ListItemIcon sx={{color: 'text.secondary', mr: 2}} key={'conceptLoadIcon'}>
                        <AddIcon/>
                    </ListItemIcon>
                    <ListItemText key={'conceptLoadText'}>
                        <Typography variant='h6' color='primary.light'>
                            Load more Concepts
                        </Typography>
                    </ListItemText>
                </ListItem>
            </ListItemButton>
        </List>)
    }, [concepts, selectedConceptIdx, conceptsUsed])

    const handleChipClick = (word: CorpusWord) => {
        let input: [string, number] = [word.text, word.index]
        word.nounFlag ? dispatch(addNoun(input)) : dispatch(addAdjective(input))
    }

    const customSubmitFactory = (isNoun: boolean) => {
        return (text: string) => {
            postRequest('corpus', {word: text, isNoun: isNoun}).then(data => {
                if (data) {
                    let result: CorpusWord = data.result
                    let input: [string, number] = [result.text, result.index]
                    isNoun ? dispatch(addNoun(input)) : dispatch(addAdjective(input))
                }
            })
        }
    }

    const suggestedAdjectives = useMemo(() => {
        return <Box sx={{bgcolor: '#252525', width: '100%', p: '5px', border: '2px solid', borderColor: '#161616'}}>
            <Typography variant='subtitle2' sx={{color: '#c2c2c2'}}>Select suggested adjectives:</Typography>
            <Box sx={{height: '73px', overflow: 'auto'}}>
                {adjectives && adjectives.map((word, index) => <PhraseChip key={'adjChip' + index}
                                                                           token={word.text}
                                                                           phraseIdx={word.index} isNoun={false}
                                                                           handleClick={() => handleChipClick(word)}/>)}
            </Box>
            <ButtonTextfield tfLabel='Custom Adjective' buttonText='Add to Concept'
                             submitFunc={customSubmitFactory(false)} clearOnSubmit/>
        </Box>
    }, [adjectives])

    const suggestedNouns = useMemo(() => {
        return <Box sx={{bgcolor: '#252525', width: '100%', p: '5px', border: '2px solid', borderColor: '#161616'}}>
            <Typography variant='subtitle2' sx={{color: '#c2c2c2'}}>Select suggested nouns:</Typography>
            <Box sx={{height: '73px', overflow: 'auto'}}>
                {nouns && nouns.map((word, index) => <PhraseChip key={'nounChip' + index}
                                                                 token={word.text}
                                                                 phraseIdx={word.index} isNoun={true}
                                                                 handleClick={() => handleChipClick(word)}/>)}
            </Box>
            <ButtonTextfield tfLabel='Custom Noun' buttonText='Add to Concept'
                             submitFunc={customSubmitFactory(true)} clearOnSubmit/>
        </Box>
    }, [nouns])

    useEffect(() => {
        loadSuggestedConcepts().then(data => data && setConcepts(data.result))
        loadSuggestedAdjectives().then(data => data && setAdjectives(data.result))
        loadSuggestedNouns().then(data => data && setNouns(data.result))
    }, []);

    useEffect(() => {
        if (concepts && concepts.length > 0 && concNouns.length === 0) {
            setConceptsUsed(Array(concepts.length).fill(false));
        }
    }, [concepts, concNouns]);

    return <>
        <Typography variant='h6'>Select suggested Concepts or build new ones</Typography>
        <Divider sx={{my: 1}}/>
        <Typography variant='subtitle1' sx={{mb: 0.6, color: '#c2c2c2'}}>Choose suggested, already existing
            concepts:</Typography>
        <Box sx={{height: '145px', overflow: 'auto', border: '2px solid', mb: 0.5, borderColor: '#161616'}}>
            {suggestedConcepts}
        </Box>
        <Button sx={{textTransform: 'none', fontSize: '12pt', width: '70%', height: '30px', mb: 1}}
                variant='contained' onClick={submitConceptClick}>
            <b>Add Concept to your Annotation</b>
        </Button>
        <Divider sx={{mb: 1}}/>
        <Typography variant='h6' sx={{mb: 1}}>Build a custom concept:</Typography>
        {suggestedAdjectives}
        <Divider/>
        {suggestedNouns}
    </>
}

export default ConceptsController
