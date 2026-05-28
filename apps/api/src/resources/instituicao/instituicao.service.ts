import { Injectable } from '@nestjs/common';
import { CreateInstituicaoDto } from './dto/create-instituicao.dto';
import { UpdateInstituicaoDto } from './dto/update-instituicao.dto';
import { PrismaService } from 'src/prisma/prisma.service';

@Injectable()
export class InstituicaoService {
  constructor(private readonly prisma: PrismaService) {}
  create(createInstituicaoDto: CreateInstituicaoDto) {
    return 'This action adds a new instituicao';
  }

  findAll() {
    return this.prisma.instituicao.findMany({
      omit: {
        criadoEm: true,
        atualizadoEm: true,
      },
    });
  }

  findOne(id: number) {
    return `This action returns a #${id} instituicao`;
  }

  update(id: number, updateInstituicaoDto: UpdateInstituicaoDto) {
    return `This action updates a #${id} instituicao`;
  }

  remove(id: number) {
    return `This action removes a #${id} instituicao`;
  }
}
