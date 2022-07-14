package lib

import (
	"fmt"
	"hash/crc32"
	"math/bits"
)

type RollingCRC struct {
	size  int    // size of the CRC window
	crc   uint32 // *unmasked* CRC of the window (no 0xfffffff prefix and not inverted)
	zero  uint32 // CRC of length 0x00 bytes, including the 0xfffffff prefix
	one   uint32 // CRC of 0x80 followed by length-1 0x00 bytes, with no 0xfffffff prefix
	z     []byte // slice of 0x00 bytes
	table *crc32.Table
}

func NewRollingCRC(table *crc32.Table) *RollingCRC {
	r := &RollingCRC{table: table}
	r.Reset()
	return r
}

func (d *RollingCRC) Reset() {
	d.crc = 0
	d.zero = crc32.Checksum([]byte{0}, d.table)
	d.one = crc32.Update(^uint32(0), d.table, []byte{0x80}) // ^uint32(0) cancels out the prefix
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
	c := d.crc
	if d.size > 0 {
		for i := range old {
			// subtract the old byte
			c ^= ^crcmulTable(d.one, old[i], d.table)
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
		z := d.z
		if cap(z) < n {
			z = make([]byte, n)
			d.z = z
		}
		z = z[:n]
		if d.size == 0 {
			z = z[1:] //compensate for the initial byte in each crc
		}
		d.zero = crc32.Update(d.zero, d.table, z)
		d.one = crc32.Update(d.one, d.table, z)
		d.size += n
	}
	d.crc = c
}

func (d *RollingCRC) Sum32() uint32 {
	return d.crc ^ d.zero
}

/// multiplies a 32-bit CRC by a 8-bit value
func crcmulTable(crc uint32, val uint8, t *crc32.Table) uint32 {
	c := uint64(bits.Reverse32(^crc))
	a := uint64(bits.Reverse8(val))
	// multiply
	m := c*(a&0x80) ^ c*(a&0x40) ^ c*(a&0x20) ^ c*(a&0x10) ^
		c*(a&8) ^ c*(a&4) ^ c*(a&2) ^ c*(a&1)
	m = bits.Reverse64(m)
	// reduce
	crc = uint32(m>>32) ^ t[byte(m>>24)]
	return ^crc
}
