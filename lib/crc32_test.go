package lib

import (
	"fmt"
	"hash/crc32"
	"testing"
)

func crcmul(crc uint32, val uint8) uint32 {
	return ^crcmulUnmasked(^crc, val, crc32.IEEETable)
}

func TestCrcmul(t *testing.T) {
	want := crc32.ChecksumIEEE([]byte{0})
	a := crcmul(0, 0x08)
	b := crcmul(a, 0x08)
	//b := a
	if b != want {
		t.Errorf("%08x != %08x", want, b)
	}
}

func TestCrcmul2(t *testing.T) {
	data := make([]byte, 256)
	for i := range data {
		data[i] = byte(i)
	}

	tab := crc32.IEEETable
	c := uint32(0)
	zero := crc32.ChecksumIEEE([]byte{0})
	one := crc32.Update(^uint32(0), tab, []byte{0x80})
	for i := 1; i <= len(data); i++ {
		want := crc32.ChecksumIEEE(data[len(data)-i:])

		c ^= ^crcmul(one, data[len(data)-i])
		crc := c ^ zero
		zero = crc32.Update(zero, tab, []byte{0})
		one = crc32.Update(one, tab, []byte{0})

		if want != crc {
			t.Errorf("%d: got %08x, want %08x", i, crc, want)
		}
	}
}

func TestCrcmul3(t *testing.T) {
	data := make([]byte, 256)
	for i := range data {
		data[i] = byte(i)
	}

	tab := crc32.IEEETable
	c := uint32(0)
	zero := crc32.ChecksumIEEE([]byte{0})
	one := crc32.Update(^uint32(0), tab, []byte{0x80})

	// start in the middle
	c = ^crc32.Update(^c, tab, data[128:])
	z := make([]byte, 128)
	zero = crc32.Update(zero, tab, z[1:])
	one = crc32.Update(one, tab, z[1:])

	{
		want := crc32.ChecksumIEEE(data[128:])
		got := c ^ zero
		if want != got {
			t.Errorf("setup: got %08x, want %08x", got, want)
			return
		}
		zero = crc32.Update(zero, tab, z[:1])
		one = crc32.Update(one, tab, z[:1])
	}

	for i := 129; i <= len(data); i++ {
		want := crc32.ChecksumIEEE(data[len(data)-i:])

		c ^= ^crcmul(one, data[len(data)-i])
		crc := c ^ zero
		zero = crc32.Update(zero, tab, []byte{0})
		one = crc32.Update(one, tab, []byte{0})

		if want != crc {
			t.Errorf("%d: got %08x, want %08x", i, crc, want)
		}
	}
}

func TestRollingCRC(t *testing.T) {
	data := make([]byte, 256)
	for i := range data {
		data[i] = byte(i)
	}

	tab := crc32.IEEETable
	d := NewRollingCRC(tab)
	d.Update(nil, data)
	got := d.Sum32()
	want := crc32.Checksum(data, tab)
	if got != want {
		t.Errorf("whole data: got %08x, want %08x", got, want)
	}

	w := 32
	for _, stride := range []int{1, 4} {
		*d = *NewRollingCRC(tab)
		for i := 0; i < len(data)-w; i += stride {
			if i == 0 {
				d.Update(nil, data[:w])
			} else {
				d.Update(data[i-stride:i], data[w+i-stride:w+i])
			}
			got := d.Sum32()
			want := crc32.Checksum(data[i:i+w], tab)
			if got != want {
				t.Errorf("i=%d:%d, width=%d, stride=%d: got %08x, want %08x", i, i+w, w, stride, got, want)
				break
			}
		}
	}
}

var sink uint32

func BenchmarkRollingCRC(b *testing.B) {
	for bits := 8; bits < 12; bits++ {
		data := make([]byte, 1<<bits)
		for i := range data {
			data[i] = byte(i)
		}

		b.Run(fmt.Sprint(1<<bits), func(b *testing.B) {
			b.SetBytes(int64(len(data)))
			tab := crc32.IEEETable
			d := NewRollingCRC(tab)
			for j := 0; j < b.N; j++ {
				w := 32
				stride := 4
				d.Reset()
				for i := 0; i < len(data)-w; i += stride {
					if i == 0 {
						d.Update(nil, data[:w])
					} else {
						d.Update(data[i-stride:i], data[w+i-stride:w+i])
					}
				}
				sink += d.Sum32()
			}
		})
	}
}

func TestMul32(t *testing.T) {
	tab := crc32.IEEETable
	for _, tt := range []struct {
		a, b, want uint32
	}{
		{0x8000, 0x8000, crc32.IEEE},
		{1 << 31, 0xffffffff, 0xffffffff},
		{0xffffffff, 1 << 31, 0xffffffff},
		{0x80, ^crc32.ChecksumIEEE([]byte{1, 2, 3, 4}), ^crc32.ChecksumIEEE([]byte{1, 2, 3, 4, 0, 0, 0})},
		{crc32.IEEE, 0xffffffff, ^crc32.ChecksumIEEE([]byte{0, 0, 0, 0})},
	} {
		got := crcmul32(tt.a, tt.b, tab)
		if got != tt.want {
			t.Errorf("mul(%08x, %08x) = %08x, want %08x", tt.a, tt.b, got, tt.want)
		}
	}
}
