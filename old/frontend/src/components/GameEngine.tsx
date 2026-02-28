'use client'

import type { GameBlueprint } from '@/types/gameBlueprint'
import { LabelDiagramGame } from './templates/LabelDiagramGame'
import { ImageHotspotGame } from './templates/ImageHotspotGame'
import { SequenceBuilderGame } from './templates/SequenceBuilderGame'
import { TimelineOrderGame } from './templates/TimelineOrderGame'
import { BucketSortGame } from './templates/BucketSortGame'
import { MatchPairsGame } from './templates/MatchPairsGame'
import { MatrixMatchGame } from './templates/MatrixMatchGame'
import { ParameterPlaygroundGame } from './templates/ParameterPlaygroundGame'
import { GraphSketcherGame } from './templates/GraphSketcherGame'
import { VectorSandboxGame } from './templates/VectorSandboxGame'
import { StateTracerCodeGame } from './templates/StateTracerCodeGame'
import { SpotTheMistakeGame } from './templates/SpotTheMistakeGame'
import { ConceptMapBuilderGame } from './templates/ConceptMapBuilderGame'
import { MicroScenarioBranchingGame } from './templates/MicroScenarioBranchingGame'
import { DesignConstraintBuilderGame } from './templates/DesignConstraintBuilderGame'
import { ProbabilityLabGame } from './templates/ProbabilityLabGame'
import { BeforeAfterTransformerGame } from './templates/BeforeAfterTransformerGame'
import { GeometryBuilderGame } from './templates/GeometryBuilderGame'

interface GameEngineProps {
  blueprint: GameBlueprint
}

export function GameEngine({ blueprint }: GameEngineProps) {
  switch (blueprint.templateType) {
    case 'LABEL_DIAGRAM':
      return <LabelDiagramGame blueprint={blueprint} />
    case 'IMAGE_HOTSPOT_QA':
      return <ImageHotspotGame blueprint={blueprint} />
    case 'SEQUENCE_BUILDER':
      return <SequenceBuilderGame blueprint={blueprint} />
    case 'TIMELINE_ORDER':
      return <TimelineOrderGame blueprint={blueprint} />
    case 'BUCKET_SORT':
      return <BucketSortGame blueprint={blueprint} />
    case 'MATCH_PAIRS':
      return <MatchPairsGame blueprint={blueprint} />
    case 'MATRIX_MATCH':
      return <MatrixMatchGame blueprint={blueprint} />
    case 'PARAMETER_PLAYGROUND':
      return <ParameterPlaygroundGame blueprint={blueprint} />
    case 'GRAPH_SKETCHER':
      return <GraphSketcherGame blueprint={blueprint} />
    case 'VECTOR_SANDBOX':
      return <VectorSandboxGame blueprint={blueprint} />
    case 'STATE_TRACER_CODE':
      return <StateTracerCodeGame blueprint={blueprint} />
    case 'SPOT_THE_MISTAKE':
      return <SpotTheMistakeGame blueprint={blueprint} />
    case 'CONCEPT_MAP_BUILDER':
      return <ConceptMapBuilderGame blueprint={blueprint} />
    case 'MICRO_SCENARIO_BRANCHING':
      return <MicroScenarioBranchingGame blueprint={blueprint} />
    case 'DESIGN_CONSTRAINT_BUILDER':
      return <DesignConstraintBuilderGame blueprint={blueprint} />
    case 'PROBABILITY_LAB':
      return <ProbabilityLabGame blueprint={blueprint} />
    case 'BEFORE_AFTER_TRANSFORMER':
      return <BeforeAfterTransformerGame blueprint={blueprint} />
    case 'GEOMETRY_BUILDER':
      return <GeometryBuilderGame blueprint={blueprint} />
    default:
      return (
        <div className="p-8 text-center">
          <p className="text-red-600">
            Unsupported template: {(blueprint as any).templateType}
          </p>
        </div>
      )
  }
}

