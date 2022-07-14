package lib

import (
	"fmt"
	"hash/crc32"
)

type RollingCRC struct {
	size  int    // size of the CRC window
	crc   uint32 // *unmasked* CRC of the window (no 0xfffffff prefix and not inverted)
	zero  uint32 // CRC of length 0x00 bytes, including the 0xfffffff prefix
	one   uint32 // *unmasked* CRC of 0x80 followed by length-1 0x00 bytes
	table *crc32.Table
}

func NewRollingCRC(table *crc32.Table) *RollingCRC {
	r := &RollingCRC{table: table}
	r.Reset()
	return r
}

var zeroByte = []byte{0}

func (d *RollingCRC) Reset() {
	d.crc = 0
	d.zero = crc32.Checksum(zeroByte, d.table)
	d.one = d.table[0x80] // == d.zero ^ crc32.Checksum([]byte{0x80}, d.table)
}

// update rolls the CRC forwards, subtracting old bytes from the left
// and adding new bytes to the right.
// there must be at least as many new bytes as old bytes.
// if there are more new bytes, then this is the same as calling
// update with equal length slices followed by adding the excess new bytes.
// the old bytes must be exactly the bytes that were added d.Size bytes ago,
// or else the result is undefined.
func (d *RollingCRC) Update(old, new []byte) {
	if len(old) > d.size {
		// TODO: can we do something clever here?
		panic(fmt.Errorf("rolling update: tried to shift %d bytes out of a %d-size window", len(old), d.size))
	}
	if len(old) > len(new) {
		panic(fmt.Errorf("rolling update: cannot decrease window size, old > new [%d > %d]", len(old), len(new)))
	}
	c := d.crc
	if d.size > 0 {
		for i := range old {
			// subtract the old byte
			c ^= crcmulUnmasked(d.one, old[i], d.table)
			// add the new byte
			//c = ^crc32.Update(^c, d.table, new[i:i+1]) // unmasked update
			c = d.table[byte(c)^new[i]] ^ (c >> 8) // unmasked update
		}
	}

	// increase the size of the window
	if len(old) < len(new) {
		// add the new bytes
		c = ^crc32.Update(^c, d.table, new[len(old):]) // unmasked update
		// increase zero and one to match
		n := len(new) - len(old)
		z := make([]byte, n)
		if d.size == 0 {
			z = z[1:] //compensate for the initial byte in each crc
		}
		d.zero = crc32.Update(d.zero, d.table, z)
		d.one = ^crc32.Update(^d.one, d.table, z) // unmasked update
		d.size += n
		// we could hold onto z for later but increasing the length
		// is uncommon, and stashing it on d would force it to be heap
		// allocated.
		// maybe a sync.Pool would be appropriate if the allocation
		// proves to be a problem.
	}
	d.crc = c
}

func (d *RollingCRC) Sum32() uint32 {
	return d.crc ^ d.zero
}

// multiplies an unmasked 32-bit CRC by a 8-bit polynomial
func crcmulUnmasked(crc uint32, val uint8, t *crc32.Table) uint32 {
	c := uint64(crc) << 1
	a := uint64(val)
	m := c*(a&0x80) ^ c*(a&0x40) ^ c*(a&0x20) ^ c*(a&0x10) ^
		c*(a&8) ^ c*(a&4) ^ c*(a&2) ^ c*(a&1)

	// reduce
	crc = uint32(m>>8) ^ t[byte(m)]
	return crc
}
