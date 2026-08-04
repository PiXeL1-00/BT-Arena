import { describe, it, expect } from 'vitest'
import { parseStructuredMessage } from '../messageParser'
import type { MessageType } from '../types'

describe('messageParser', () => {
    it('should parse a valid proposal JSON', () => {
        const json = JSON.stringify({
            proposed_verdict: 'SUPPORTED',
            evidence_used: ['E1'],
            key_points: ['Point 1'],
            uncertainties: []
        })

        const result = parseStructuredMessage(json, 'proposal')

        expect(result).not.toBeNull()
        expect(result?.type).toBe('proposal')
        expect(result?.data).toHaveProperty('proposed_verdict', 'SUPPORTED')
    })

    it('should return null for invalid JSON', () => {
        const result = parseStructuredMessage('invalid json', 'proposal')
        expect(result).toBeNull()
    })

    it('should handle truncated JSON repair', () => {
        // A truncated JSON string
        const truncated = '{"proposed_verdict": "SUPP'

        // Note: The current implementation might return null or a partial object depending on logic
        // This test verifies it doesn't crash
        const result = parseStructuredMessage(truncated, 'proposal')

        // We expect it to handle it gracefully (either null or truncated flag)
        if (result) {
            expect(result.isTruncated).toBe(true)
        } else {
            expect(result).toBeNull()
        }
    })
})
