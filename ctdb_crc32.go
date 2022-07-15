package main

import (
	"flag"
	"fmt"
	"hash/crc32"
	"io"
	"log"
	"os"
	"runtime/pprof"
	"strconv"

	"github.com/magical/audiotools/lib"
)

const (
	FrameSamples = 588
	FrameBytes   = FrameSamples * 4
)

func main() {
	log.SetFlags(0)
	flag.Parse()

	leadin := 10 * FrameSamples
	leadout := 10 * FrameSamples // minimum, will be adjusted later

	// parse CRC arguments
	want := make(map[uint32]bool)
	for _, arg := range flag.Args() {
		if v, err := strconv.ParseUint(arg, 16, 32); err == nil {
			want[uint32(v)] = true
		} else {
			log.Fatal(err)
		}
	}
	//fmt.Println()
	if len(want) == 0 {
		log.Fatal("no args")
	}

	input := os.Stdin

	const doProfile = false
	if doProfile {
		cpufile, _ := os.Create("/tmp/ctdb_cpu.prof")
		defer cpufile.Close()
		pprof.StartCPUProfile(cpufile)
		defer pprof.StopCPUProfile()
	}

	// we want to keep a circular buffer of 30*588 samples
	// we need at least 20 to detect the end
	// and +10 gives us some room to try all the leadin samples

	var fileLength int64

	// start the leadin/leadout buffer
	buffer := make([]byte, 30*FrameBytes) // about 70 kB

	// if we get a short read, that's all right
	n, err := readUntilErr(input, buffer)
	fileLength += int64(n)
	if err != nil && err != io.EOF {
		log.Fatal(err)
	}

	// before we go any further, we need to save a copy of the buffer
	// (which contains the leadin frames) so we have it for reference later
	leadinBuf := make([]byte, len(buffer))
	copy(leadinBuf, buffer)

	r := lib.NewRollingCRC(crc32.IEEETable)

	// if we hit EOF, we're done reading and can proceed to the rolling calculation
	// if not then we have more data to read
	if err == nil {
		// the old buffer is full of 30 frames of data
		// we can process some of that but we don't know how much yet
		// since there may only be 1 sample left in the input stream

		// (note that the io.Reader docs state that Read may use all of the buffer as a scratch space,
		// so we would need two buffers anyway)

		back := make([]byte, len(buffer))
		for err == nil {
			// read some more input
			n, err = readUntilErr(input, back)
			fileLength += int64(n)
			if err != nil && err != io.EOF {
				log.Fatal(err)
			}

			if err == io.EOF {
				// process as many bytes of the old buffer as we just
				// read - that's how many are about to be discarded
				r.Update(nil, buffer[:n])

				// truncate buffers
				// now buffer + back gives us the 30 frames of leadout we're looking fo
				buffer = buffer[n:]
				back = back[:n]

				buffer = append(buffer, back...) // FIXME
				break
			}

			// we filled the new buffer, so process all the bytes of the old buffer
			// and then swap them for the next loop iteration
			r.Update(nil, buffer)
			buffer, back = back, buffer
		}
	}

	// we need at *least* 10 leadin and 10 leadout frames for there to be any data to checksum
	const minFileLength = 20 * FrameBytes

	if fileLength < minFileLength {
		log.Fatalf("error: input length %d is too short", fileLength)
	}
	if fileLength%4 != 0 {
		log.Printf("warning: input length %d is not a multiple of 4 bytes", fileLength)
	}

	fullLength := fileLength / 4

	if fullLength%FrameSamples != 0 {
		log.Printf("warning: audio length %d is not a multiple of %d samples", fullLength, FrameSamples)
	}

	leadout += int(fullLength % int64(leadout))

	tmp := len(buffer) - 4*(leadin+leadout) - len(buffer)%4
	r.Update(nil, buffer[:tmp])
	buffer = buffer[tmp:]

	// TODO: what if buffer == leadin?

	length := fullLength - int64(leadin) - int64(leadout)
	log.Printf("leadin=%d, leadout=%d, length=%d, full=%d\n", leadin, leadout, length, fullLength)

	width := 20 * FrameSamples
	width = leadin + leadout // XXX

	log.Printf("first=%08x\n", r.Sum32())
	for i := 0; i <= width; i++ {
		c := r.Sum32()
		if want[c] {
			fmt.Printf("%d %08x\n", i-leadin, c)
		}
		if i != width {
			r.Update(leadinBuf[i*4:][:4], buffer[i*4:][:4])
		}
	}
	log.Printf("last=%08x\n", r.Sum32())

}

func readUntilErr(r io.Reader, p []byte) (int, error) {
	nn := 0
	for len(p) > 0 {
		n, err := r.Read(p)
		nn += n
		if err != nil {
			return nn, err
		}
		p = p[n:]
	}
	return nn, nil
}
