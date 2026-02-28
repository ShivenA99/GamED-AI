'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface TreeNode {
  id: number | string
  value: any
  left?: number | string | null
  right?: number | string | null
  parent?: number | string | null
}

interface TreeVisualizerProps {
  treeNodes: TreeNode[]
  traversalType?: 'inorder' | 'preorder' | 'postorder' | 'level_order' | null
  animationSpeed?: number // milliseconds per node
  onTraversalComplete?: () => void
  showTree?: boolean // Whether to show the tree structure
}

interface TreeNodeWithPosition extends TreeNode {
  x: number
  y: number
  visited: boolean
  isCurrent: boolean
  visitOrder?: number
}

export function TreeVisualizer({
  treeNodes,
  traversalType,
  animationSpeed = 500,
  onTraversalComplete,
  showTree = true
}: TreeVisualizerProps) {
  const [visitedNodes, setVisitedNodes] = useState<Set<string | number>>(new Set())
  const [currentNode, setCurrentNode] = useState<string | number | null>(null)
  const [visitOrder, setVisitOrder] = useState<Map<string | number, number>>(new Map())
  const [isAnimating, setIsAnimating] = useState(false)

  // Build tree structure from nodes
  const treeMap = useMemo(() => {
    const map = new Map<string | number, TreeNode>()
    treeNodes.forEach(node => {
      map.set(node.id, node)
    })
    return map
  }, [treeNodes])

  // Find root node (node without parent)
  const rootNode = useMemo(() => {
    return treeNodes.find(node => !node.parent) || treeNodes[0]
  }, [treeNodes])

  // Calculate positions for tree layout
  const positionedNodes = useMemo(() => {
    if (!rootNode) return []
    
    const positions = new Map<string | number, { x: number; y: number }>()
    const nodeMap = new Map<string | number, TreeNodeWithPosition>()
    
    // Calculate tree depth
    const getDepth = (nodeId: string | number | null | undefined, depth = 0): number => {
      if (!nodeId) return depth
      const node = treeMap.get(nodeId)
      if (!node) return depth
      const leftDepth = node.left ? getDepth(node.left, depth + 1) : depth
      const rightDepth = node.right ? getDepth(node.right, depth + 1) : depth
      return Math.max(leftDepth, rightDepth)
    }
    
    const maxDepth = getDepth(rootNode.id)
    const nodeWidth = 80
    const nodeHeight = 100
    const levelHeight = 120
    
    // Calculate positions using recursive layout
    const layoutNode = (nodeId: string | number | null | undefined, x: number, y: number, level: number): void => {
      if (!nodeId) return
      const node = treeMap.get(nodeId)
      if (!node) return
      
      positions.set(nodeId, { x, y })
      
      const childrenCount = (node.left ? 1 : 0) + (node.right ? 1 : 0)
      const spacing = Math.max(150, 200 - level * 20)
      
      if (node.left) {
        layoutNode(node.left, x - spacing / (level + 1), y + levelHeight, level + 1)
      }
      if (node.right) {
        layoutNode(node.right, x + spacing / (level + 1), y + levelHeight, level + 1)
      }
    }
    
    // Start layout from root
    const startX = 400 // Center X for root
    const startY = 50
    layoutNode(rootNode.id, startX, startY, 0)
    
    // Build node map with positions
    treeNodes.forEach(node => {
      const pos = positions.get(node.id) || { x: 0, y: 0 }
      nodeMap.set(node.id, {
        ...node,
        ...pos,
        visited: visitedNodes.has(node.id),
        isCurrent: currentNode === node.id,
        visitOrder: visitOrder.get(node.id)
      })
    })
    
    return Array.from(nodeMap.values())
  }, [treeNodes, treeMap, rootNode, visitedNodes, currentNode, visitOrder])

  // Traversal algorithms
  const getTraversalOrder = (type: 'inorder' | 'preorder' | 'postorder' | 'level_order'): (string | number)[] => {
    const result: (string | number)[] = []
    
    if (type === 'level_order') {
      // BFS / Level order
      const queue: (string | number | null)[] = [rootNode.id]
      while (queue.length > 0) {
        const nodeId = queue.shift()
        if (!nodeId) continue
        const node = treeMap.get(nodeId)
        if (!node) continue
        result.push(nodeId)
        if (node.left) queue.push(node.left)
        if (node.right) queue.push(node.right)
      }
    } else {
      // DFS traversals
      const traverse = (nodeId: string | number | null | undefined) => {
        if (!nodeId) return
        const node = treeMap.get(nodeId)
        if (!node) return
        
        if (type === 'preorder') {
          result.push(nodeId)
          traverse(node.left ?? null)
          traverse(node.right ?? null)
        } else if (type === 'inorder') {
          traverse(node.left ?? null)
          result.push(nodeId)
          traverse(node.right ?? null)
        } else if (type === 'postorder') {
          traverse(node.left ?? null)
          traverse(node.right ?? null)
          result.push(nodeId)
        }
      }
      traverse(rootNode.id)
    }
    
    return result
  }

  // Animate traversal
  useEffect(() => {
    if (!traversalType || isAnimating) return
    
    setIsAnimating(true)
    setVisitedNodes(new Set())
    setCurrentNode(null)
    setVisitOrder(new Map())
    
    const order = getTraversalOrder(traversalType)
    let currentIndex = 0
    
    const animateNext = () => {
      if (currentIndex >= order.length) {
        setIsAnimating(false)
        setCurrentNode(null)
        onTraversalComplete?.()
        return
      }
      
      const nodeId = order[currentIndex]
      setCurrentNode(nodeId)
      
      // Mark as visited after a brief delay
      setTimeout(() => {
        setVisitedNodes(prev => new Set([...prev, nodeId]))
        setVisitOrder(prev => {
          const next = new Map(prev)
          next.set(nodeId, currentIndex + 1)
          return next
        })
        setCurrentNode(null)
        currentIndex++
        
        if (currentIndex < order.length) {
          setTimeout(animateNext, animationSpeed)
        } else {
          setIsAnimating(false)
          setCurrentNode(null)
          onTraversalComplete?.()
        }
      }, animationSpeed * 0.3) // Show current node for 30% of the speed
    }
    
    animateNext()
  }, [traversalType, animationSpeed, treeMap, rootNode, isAnimating, onTraversalComplete])

  // Reset when traversal type changes
  useEffect(() => {
    setVisitedNodes(new Set())
    setCurrentNode(null)
    setVisitOrder(new Map())
    setIsAnimating(false)
  }, [traversalType])

  if (!showTree || !rootNode) {
    return null
  }

  return (
    <div className="w-full overflow-x-auto py-8">
      <svg 
        className="w-full" 
        viewBox="0 0 800 500" 
        style={{ minHeight: '500px', width: '100%', maxWidth: '800px' }}
      >
        {/* Render edges first (so they appear behind nodes) */}
        {positionedNodes.map(node => {
          const edges: JSX.Element[] = []
          if (node.left) {
            const leftNode = positionedNodes.find(n => n.id === node.left)
            if (leftNode) {
              edges.push(
                <line
                  key={`edge-${node.id}-left`}
                  x1={node.x}
                  y1={node.y + 40}
                  x2={leftNode.x}
                  y2={leftNode.y - 40}
                  stroke={visitedNodes.has(node.id) && visitedNodes.has(node.left) ? '#10b981' : '#94a3b8'}
                  strokeWidth="2"
                  className="transition-colors duration-300"
                />
              )
            }
          }
          if (node.right) {
            const rightNode = positionedNodes.find(n => n.id === node.right)
            if (rightNode) {
              edges.push(
                <line
                  key={`edge-${node.id}-right`}
                  x1={node.x}
                  y1={node.y + 40}
                  x2={rightNode.x}
                  y2={rightNode.y - 40}
                  stroke={visitedNodes.has(node.id) && visitedNodes.has(node.right) ? '#10b981' : '#94a3b8'}
                  strokeWidth="2"
                  className="transition-colors duration-300"
                />
              )
            }
          }
          return edges
        }).flat()}

        {/* Render nodes */}
        <AnimatePresence>
          {positionedNodes.map(node => {
            const isVisited = visitedNodes.has(node.id)
            const isCurrent = currentNode === node.id
            const order = visitOrder.get(node.id)
            
            return (
              <g key={node.id}>
                {/* Node circle */}
                <motion.circle
                  cx={node.x}
                  cy={node.y}
                  r={isCurrent ? 35 : 30}
                  fill={isCurrent 
                    ? '#3b82f6' 
                    : isVisited 
                      ? '#10b981' 
                      : '#ffffff'}
                  stroke={isCurrent 
                    ? '#1d4ed8' 
                    : isVisited 
                      ? '#059669' 
                      : '#3b82f6'}
                  strokeWidth={isCurrent ? 4 : isVisited ? 3 : 2}
                  className="transition-all duration-300"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{
                    opacity: 1,
                    scale: isCurrent ? [1, 1.2, 1] : isVisited ? 1.1 : 1,
                  }}
                  transition={{
                    duration: isCurrent ? animationSpeed / 1000 : 0.3,
                    repeat: isCurrent ? Infinity : 0,
                    ease: "easeInOut",
                    type: "spring",
                    stiffness: 300
                  }}
                />
                
                {/* Node value */}
                <text
                  x={node.x}
                  y={node.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="text-lg font-bold fill-gray-900 pointer-events-none select-none"
                  style={{ fontSize: '16px', fontWeight: 'bold' }}
                >
                  {node.value}
                </text>
                
                {/* Visit order indicator */}
                {order && (
                  <motion.text
                    x={node.x + 25}
                    y={node.y - 25}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="text-xs font-bold fill-blue-600 pointer-events-none select-none"
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.1 }}
                    style={{ fontSize: '12px', fontWeight: 'bold' }}
                  >
                    #{order}
                  </motion.text>
                )}
              </g>
            )
          })}
        </AnimatePresence>
      </svg>
    </div>
  )
}

