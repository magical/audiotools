package lib

import (
	"fmt"
	"hash/crc32"
)

type RollingCRC struct {
	size int    // size of the CRC window
	crc  uint32 // *unmasked* CRC of the window (no 0xfffffff prefix and not inverted)
	zero uint32 // CRC of length 0x00 bytes, including the 0xfffffff prefix
	// *unmasked* CRC of 0x80 followed by length-1 0x00 bytes
	// represents the polynomial x^(32+length*8)
	one uint32
	// inverted CRC of 1 followed by xlen*8 zeros
	// represents the polynomial x^(xlen*8)
	x     uint32
	xlen  int
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
	if d.size > 0 {
		c := d.crc
		for i := range old {
			// subtract the old byte
			c ^= crcmulUnmasked(d.one, old[i], d.table)
			// add the new byte
			//c = ^crc32.Update(^c, d.table, new[i:i+1]) // unmasked update
			c = d.table[byte(c)^new[i]] ^ (c >> 8) // unmasked update
		}
		d.crc = c
	}

	// increase the size of the window
	if len(old) < len(new) {
		d.extend(new[len(old):])
	}
}

func (d *RollingCRC) extend(buf []byte) {
	// add the new bytes
	d.crc = ^crc32.Update(^d.crc, d.table, buf) // unmasked update

	// increase zero and one to match
	// we could update them separately by appending zero bytes,
	// like so
	//     z := make([]byte, n)
	//     zero = crc32.Update(zero, d.table, z)
	//     one = ^crc32.Update(^one, d.table, z)
	// but this is somewhat expensive.
	// instead we do one update operation to get a large power of x modulo
	// the CRC polynomial and multiply d.zero and d.one by it.
	//
	// we also cache the value so that if the caller does multiple updates
	// with the same buffer size we don't have keep redoing the CRC update
	// (and allocating a new buffer).
	n := len(buf)
	if d.size == 0 {
		n-- // compensate for the initial byte in each crc
	}
	if d.xlen == 0 || d.xlen > n {
		d.x = 1 << 31
		d.xlen = 0
	}
	if d.xlen < n {
		z := make([]byte, n-d.xlen)
		d.x = ^crc32.Update(^d.x, d.table, z)
		d.xlen += len(z)
	}
	d.one = crcmul32(d.one, d.x, d.table)
	d.zero = ^crcmul32(^d.zero, d.x, d.table)
	d.size += len(buf)
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

func crcmul32(crc, crc2 uint32, t *crc32.Table) uint32 {
	c := uint64(0)

	c ^= uint64(crcmulUnmasked(crc, byte(crc2), t)) << 0
	c ^= uint64(crcmulUnmasked(crc, byte(crc2>>8), t)) << 8
	c ^= uint64(crcmulUnmasked(crc, byte(crc2>>16), t)) << 16
	c ^= uint64(crcmulUnmasked(crc, byte(crc2>>24), t)) << 24

	c = (c >> 8) ^ uint64(t[byte(c)])
	c = (c >> 8) ^ uint64(t[byte(c)])
	c = (c >> 8) ^ uint64(t[byte(c)])
	return uint32(c)
}
